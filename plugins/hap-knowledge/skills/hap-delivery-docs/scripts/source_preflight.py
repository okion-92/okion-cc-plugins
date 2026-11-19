"""Collect current official sources, bind reviewed baselines, and gate delivery output."""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError

from fetch_diff import _extract_metadata

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = {'deploy', 'ops', 'migration', 'arch', 'cred', 'faq', 'resource', 'checklist'}
DEFAULT_OUTPUTS = 'deploy,ops,arch,cred,faq,resource,checklist'
HOSTS = {'docs-pdop.mingdao.com', 'docs-pd.mingdao.com',
         'docs-pdop.nocoly.com', 'docs-pd.nocoly.com'}
MAX_AGE = timedelta(hours=24)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def url_key(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in HOSTS or parsed.port not in (None, 443) or parsed.username:
        raise ValueError('仅接受 HAP 官方 HTTPS 文档地址: ' + url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip('/') or '/', '', ''))


def fresh(stamp):
    dt = datetime.fromisoformat(stamp)
    age = datetime.now(timezone.utc) - dt
    return -timedelta(minutes=5) <= age <= MAX_AGE


def outputs(value):
    selected = set(value.split(',')) if isinstance(value, str) else set(value)
    if not selected or selected - OUTPUTS:
        raise ValueError('未知或空的产物范围: ' + str(value))
    return sorted(selected)


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.all_text, self.main_text = [], [], []
        self.main_depth = 0
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag in ('main', 'article'):
            self.main_depth += 1
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
            if self.main_depth:
                self.main_text.append(attrs['href'])

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden-1)
        if tag in ('main', 'article'):
            self.main_depth = max(0, self.main_depth-1)

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.all_text.append(data.strip())
            if self.main_depth:
                self.main_text.append(data.strip())


class OfficialRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        url_key(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url):
    url_key(url)
    with build_opener(OfficialRedirect()).open(Request(url, headers={'User-Agent': 'Mozilla/5.0 HAP-delivery-preflight'}), timeout=25) as response:
        final = url_key(response.url)
        content = response.read(8_000_001)
        if len(content) > 8_000_000:
            raise ValueError('官方页面超过 8MB，请通过浏览工具采集正文')
        parser = Page()
        parser.feed(content.decode('utf-8'))
    text = '\n'.join(parser.main_text or parser.all_text)
    if len(text) < 40:
        raise ValueError('页面没有可核验正文: ' + url)
    return {'url': final, 'content': text, 'links': [urljoin(final+'/', link) for link in parser.links],
            'fetched_at': now(), 'method': 'https'}


def canonical(url):
    path = urlsplit(url).path.strip('/').split('/')
    return '/'.join(p for p in path if not re.fullmatch(r'(?:[a-z]+-)?\d+(?:\.\d+)+(?:-.*)?', p))


def version_key(value):
    found = re.findall(r'\d+(?:\.\d+)+', value)
    return max((tuple(map(int, v.split('.'))) for v in found), default=tuple(map(int, re.findall(r'\d+', value))))


def discover(seed, links):
    choices = {url_key(seed)}
    for link in links:
        try:
            candidate = url_key(link)
        except ValueError:
            continue
        if canonical(candidate) == canonical(seed) and urlsplit(candidate).hostname == urlsplit(seed).hostname:
            choices.add(candidate)
    return max(sorted(choices), key=version_key)


def baseline_hashes(root=None):
    root = root or ROOT
    result = {}
    for folder in ('scripts', 'assets', 'templates', 'reference'):
        for path in (root/folder).rglob('*'):
            if path.is_file() and not {'_work', '__pycache__', 'source-cache'} & set(path.parts):
                result[path.relative_to(root).as_posix()] = digest(path.read_bytes())
    return result


def source_urls(version, selected, brand):
    selected = outputs(selected)
    mapping = dict(re.findall(r'^\|\s*(\w+)\s*\|[^|]+\|\s*(https://[^\s|]+)',
                              (ROOT/'reference/source-map.md').read_text(encoding='utf-8'), re.M))
    needed = set()
    if set(selected) & {'deploy', 'ops', 'migration', 'arch', 'cred'}:
        needed.update(k for k in mapping if k.startswith('s_') == (version == 'lite')
                      and not k.startswith(('faq_', 'res_')))
    if 'faq' in selected:
        needed.update(k for k in mapping if k.startswith('faq_'))
    if set(selected) & {'resource', 'checklist'}:
        needed.update(k for k in mapping if k.startswith('res_'))
    replace = lambda url: url.replace('.mingdao.com', '.nocoly.com') if brand == 'nocoly' else url
    result = {k: replace(mapping[k]) for k in sorted(needed)}
    result['index_cluster'] = replace('https://docs-pdop.mingdao.com/deployment/cluster/')
    result['index_components'] = replace('https://docs-pd.mingdao.com/deployment/component/')
    return result


def read_page(url, bundle):
    key = url_key(url)
    if key in bundle:
        page = dict(bundle[key])
        if not fresh(page['fetched_at']) or len(page['content'].strip()) < 40:
            raise ValueError('浏览采集正文过期或为空: ' + url)
        page.update(url=url_key(page.get('url', url)), method='browser-bundle')
        return page
    return fetch(url)


def prepare(args):
    selected = outputs(args.outputs)
    bundle = {}
    if args.bundle:
        bundle = {url_key(k): v for k, v in json.loads(Path(args.bundle).read_text(encoding='utf-8')).items()}
    urls = source_urls(args.version, selected, args.brand)
    overrides = dict(item.split('=', 1) for item in args.source)
    pins = dict(item.split('=', 1) for item in args.pin)
    if (overrides or pins) and not args.reason.strip():
        raise ValueError('项目指定来源/版本必须提供 --reason，不能修改通用默认')
    if set(overrides) - set(urls):
        raise ValueError('项目来源 key 不在本次生成范围内')
    urls.update(overrides)
    report_path = Path(args.report).resolve()
    pages_dir = report_path.parent/(report_path.stem+'-pages')
    pages_dir.mkdir(parents=True, exist_ok=True)
    pages, links, errors = [], [], []
    # Read both entry points before choosing current component version pages.
    for key in sorted(urls, key=lambda key: (not key.startswith('index_'), key)):
        url = discover(urls[key], links) if not key.startswith('index_') and key not in overrides else urls[key]
        try:
            page = read_page(url, bundle)
            links.extend(page.get('links', []))
            page['status'] = 'live'
        except Exception as exc:
            if isinstance(exc, HTTPError):
                exc.close()
            cache = ROOT/'reference/source-cache'/f'{key}.json'
            if not args.allow_offline or not cache.is_file():
                errors.append(f'{key}: {exc}')
                continue
            old = json.loads(cache.read_text(encoding='utf-8'))
            page = {'url': old.get('url') or url, 'content': old['snapshot'], 'fetched_at': old['fetched_at'],
                    'method': 'dated-cache', 'status': 'offline', 'error': str(exc)}
        body = page.pop('content')
        path = pages_dir/f'{key}.txt'
        path.write_text(body, encoding='utf-8')
        page.update(key=key, sha256=digest(path.read_bytes()), file=str(path), **_extract_metadata(body))
        pages.append(page)
    record = {'schema': 1, 'created_at': now(), 'state': 'prepared', 'version': args.version, 'brand': args.brand,
              'outputs': selected, 'input_sha256': digest(Path(args.input).read_bytes()) if args.input else None,
              'architecture_sha256': digest(Path(args.architecture).read_bytes()) if args.architecture else None,
              'pins': pins, 'project_source_overrides': overrides, 'project_reason': args.reason,
              'pages': pages, 'required_keys': sorted(urls), 'errors': errors}
    report_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    if errors:
        raise ValueError('来源预检未完成；使用浏览工具采集后 --bundle 导入，不能静默生成:\n'+'\n'.join(errors))
    print(f'已采集 {len(pages)} 个来源。请核对最新版本、完整部署步骤及项目覆盖，再执行 seal: {report_path}')


def read_record(path):
    record = json.loads(Path(path).read_text(encoding='utf-8'))
    if record.get('schema') != 1 or record.get('errors') or not fresh(record['created_at']):
        raise ValueError('来源记录缺失、失败或超过24小时，重新 prepare')
    if {p['key'] for p in record['pages']} != set(record['required_keys']):
        raise ValueError('来源范围不完整')
    if set(record['required_keys']) != set(source_urls(record['version'], record['outputs'], record['brand'])):
        raise ValueError('来源记录与本次产物要求不一致')
    for page in record['pages']:
        url_key(page['url'])
        if page['status'] == 'live' and not fresh(page['fetched_at']):
            raise ValueError('来源快照已过期: '+page['key'])
        if digest(Path(page['file']).read_bytes()) != page['sha256']:
            raise ValueError('来源正文变化，请重新 prepare: '+page['key'])
    return record


def seal(args):
    record = read_record(args.report)
    if not args.note.strip():
        raise ValueError('必须记录版本、部署步骤和项目覆盖的核对说明')
    if any(p['status'] == 'offline' for p in record['pages']) and not args.allow_offline:
        raise ValueError('存在离线来源，须明确 --allow-offline 并在交付说明中列明')
    targets = {
        'deploy': ['deploy_src', 'build_streamlined.py' if record['version']=='lite' else 'build_scene.py',
                   'build_standard.py', 'gen_minio_file.py', 'fix_monitor.py'],
        'ops': ['ops_src', 'ops_build.py'], 'migration': ['mig_src', 'mig_build.py'],
        'arch': ['gen_arch.py'], 'cred': ['gen_cred.py'], 'faq': ['ref_src/faq_body.md'],
        'resource': ['ref_src/resource_body.md'], 'checklist': ['chk_src', 'chk_build.py'],
    }
    paths = set()
    for output in record['outputs']:
        for name in targets[output]:
            path = ROOT/'scripts'/name
            paths.update(path.rglob('*.md') if path.is_dir() else [path])
    baselines = '\n'.join(p.read_text(encoding='utf-8', errors='replace') for p in paths
                          if p.is_file() and not {'_work', '__pycache__'} & set(p.parts))
    stored = _extract_metadata(baselines)['versions']
    checked_pins = set()
    for page in record['pages']:
        if page['key'].startswith('index_'):
            continue
        for component, versions in page['versions'].items():
            checked_pins.add(component)
            wanted = record.get('pins', {}).get(component)
            if wanted and wanted not in versions:
                raise ValueError(f'{component} 指定版本 {wanted} 未在相应专属页面明示，请提供匹配的 --source')
            if wanted and wanted not in stored.get(component, []):
                raise ValueError(f'{component} 基线没有项目指定版本 {wanted}')
            if not wanted and component in stored and max(map(version_key, stored[component])) < max(map(version_key, versions)):
                raise ValueError(f'{component} 基线版本落后于 {page["url"]}，先完整更新下载/配置/systemd/初始化/验证步骤')
    if set(record.get('pins', {})) - checked_pins:
        raise ValueError('项目锁定版本未在本次专属来源中发现')
    record.update(state='reviewed', reviewed_at=now(), review_note=args.note, baselines=baseline_hashes())
    Path(args.report).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print('已绑定来源、基线和入参；生成时会重新检查这些指纹')


def require_preflight(kind=None, version=None, selected=None, input_path=None, architecture=None):
    report = os.environ.get('HAP_PREFLIGHT_REPORT')
    if not report:
        raise ValueError('缺少 HAP_PREFLIGHT_REPORT；先 source_preflight.py prepare，再核对并 seal')
    record = read_record(report)
    if record.get('state') != 'reviewed' or record.get('baselines') != baseline_hashes():
        raise ValueError('来源尚未复核或基线已改变；重新核对并 seal')
    wanted = set(selected or ([kind] if kind else []))
    if not wanted <= set(record['outputs']) or (version and record['version'] != version):
        raise ValueError('生成范围或部署版本与来源记录不一致')
    if 'arch' in wanted and bool(architecture) != bool(record.get('architecture_sha256')):
        raise ValueError('项目架构图与核验范围不一致；使用 gen_from_input.py --architecture 或重新 prepare')
    inp = input_path or os.environ.get('HAP_DELIVERY_INPUT')
    if (digest(Path(inp).read_bytes()) if inp else None) != record.get('input_sha256'):
        raise ValueError('入参与来源记录不一致，重新 prepare')
    if architecture is not None and digest(Path(architecture).read_bytes()) != record.get('architecture_sha256'):
        raise ValueError('项目架构图与来源记录不一致，重新 prepare')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    collect = sub.add_parser('prepare')
    collect.add_argument('--version', choices=('std', 'pro', 'lite'), required=True)
    collect.add_argument('--outputs', default=DEFAULT_OUTPUTS)
    collect.add_argument('--brand', choices=('mingdao', 'nocoly'), default='mingdao')
    collect.add_argument('--input')
    collect.add_argument('--architecture')
    collect.add_argument('--bundle')
    collect.add_argument('--source', action='append', default=[], metavar='KEY=URL')
    collect.add_argument('--pin', action='append', default=[], metavar='COMPONENT=VERSION')
    collect.add_argument('--reason', default='')
    collect.add_argument('--allow-offline', action='store_true')
    collect.add_argument('--report', required=True)
    review = sub.add_parser('seal')
    review.add_argument('--report', required=True)
    review.add_argument('--note', required=True)
    review.add_argument('--allow-offline', action='store_true')
    args = parser.parse_args()
    try:
        (prepare if args.command == 'prepare' else seal)(args)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, str(exc)+'\n')


if __name__ == '__main__':
    main()
