import argparse
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import source_preflight as pre
from fetch_diff import _extract_metadata


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hap-preflight-test-')
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(patch.stopall)
        patch.object(pre, 'ROOT', self.root).start()
        (self.root/'reference').mkdir()
        (self.root/'scripts/ref_src').mkdir(parents=True)
        (self.root/'reference/source-map.md').write_text(
            '| res_component | component | https://docs-pd.mingdao.com/deployment/component/ |\n', encoding='utf-8')
        self.baseline = self.root/'scripts/ref_src/resource_body.md'
        self.baseline.write_text('mysql-8.4.8-linux.tar.xz', encoding='utf-8')
        self.input = self.root/'input.xlsx'
        self.input.write_bytes(b'fixture input; no customer data')
        self.report = self.root/'report.json'
        self.bundle = self.root/'bundle.json'
        pages = {url: {'content': 'Official-page test fixture only. Package: mysql-8.4.8-linux.tar.xz',
                       'links': [], 'fetched_at': pre.now()}
                 for url in pre.source_urls('std', ['resource'], 'mingdao').values()}
        self.bundle.write_text(json.dumps(pages), encoding='utf-8')
        self.args = argparse.Namespace(version='std', outputs='resource', brand='mingdao',
                                      input=str(self.input), architecture=None, bundle=str(self.bundle),
                                      source=[], pin=[], reason='', allow_offline=False, report=str(self.report))
        patch.dict(os.environ, HAP_PREFLIGHT_REPORT=str(self.report), HAP_DELIVERY_INPUT=str(self.input)).start()
        patch.object(pre, 'fetch', side_effect=OSError('fixture: network unavailable')).start()

    def prepare(self):
        with redirect_stdout(io.StringIO()):
            pre.prepare(self.args)

    def seal(self, offline=False):
        with redirect_stdout(io.StringIO()):
            pre.seal(argparse.Namespace(report=str(self.report), note='Reviewed fixture steps and project scope', allow_offline=offline))

    def test_prepared_record_cannot_generate(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, '尚未复核'):
            pre.require_preflight('resource', 'std')

    def test_reviewed_record_scope_and_input(self):
        self.prepare(); self.seal()
        self.assertEqual(pre.require_preflight('resource', 'std')['state'], 'reviewed')
        with self.assertRaisesRegex(ValueError, '范围'):
            pre.require_preflight('migration', 'std')
        self.input.write_bytes(b'changed input')
        with self.assertRaisesRegex(ValueError, '入参'):
            pre.require_preflight('resource', 'std')

    def test_changed_baseline_blocks_generation(self):
        self.prepare(); self.seal()
        self.baseline.write_text('changed', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '基线'):
            pre.require_preflight('resource', 'std')

    def test_old_version_blocks_seal(self):
        self.baseline.write_text('mysql-8.0.45-linux.tar.xz', encoding='utf-8')
        self.prepare()
        with self.assertRaisesRegex(ValueError, '版本落后'):
            self.seal()

    def test_snapshot_change_blocks_generation(self):
        self.prepare(); self.seal()
        record = json.loads(self.report.read_text(encoding='utf-8'))
        Path(record['pages'][0]['file']).write_text('tampered', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '正文变化'):
            pre.require_preflight('resource', 'std')

    def test_expired_and_incomplete_records(self):
        self.prepare()
        record = json.loads(self.report.read_text(encoding='utf-8'))
        record['created_at'] = (datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
        self.report.write_text(json.dumps(record), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '24小时'):
            self.seal()
        self.prepare()
        record = json.loads(self.report.read_text(encoding='utf-8'))
        record['pages'].pop()
        self.report.write_text(json.dumps(record), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '不完整'):
            self.seal()

    def test_failed_collection_is_not_silent(self):
        self.args.bundle = None
        with self.assertRaisesRegex(ValueError, '不能静默生成'):
            self.prepare()
        self.assertTrue(json.loads(self.report.read_text(encoding='utf-8'))['errors'])

    def test_offline_needs_explicit_review_and_preserves_date(self):
        pages = json.loads(self.bundle.read_text(encoding='utf-8'))
        del pages['https://docs-pd.mingdao.com/deployment/component/']
        self.bundle.write_text(json.dumps(pages), encoding='utf-8')
        cache = self.root/'reference/source-cache'
        cache.mkdir()
        for key in ('res_component', 'index_components'):
            (cache/f'{key}.json').write_text(json.dumps({'url': 'https://docs-pd.mingdao.com/deployment/component/',
                'snapshot': 'Offline fixture version mysql-8.4.8, not a fresh online page', 'fetched_at': '2020-01-01'}), encoding='utf-8')
        self.args.allow_offline = True
        self.prepare()
        with self.assertRaisesRegex(ValueError, '离线'):
            self.seal()
        self.seal(offline=True)
        page = next(p for p in pre.require_preflight('resource')['pages'] if p['status']=='offline')
        self.assertEqual(page['fetched_at'], '2020-01-01')

    def test_latest_version_discovery_and_domain_boundary(self):
        seed = 'https://docs-pdop.mingdao.com/deployment/cluster/installation/mysql/mysql-8.0/mgr/'
        newest = seed.replace('8.0', '8.4')
        self.assertEqual(pre.discover(seed, [newest, seed, newest.replace('docs-pdop.mingdao.com','example.invalid')]), newest.rstrip('/'))
        with self.assertRaises(ValueError):
            pre.url_key('https://docs-pdop.mingdao.com@127.0.0.1/')
        with self.assertRaises(ValueError):
            pre.url_key('http://docs-pdop.mingdao.com/')

    def test_project_pin_is_scoped_and_checked(self):
        self.args.pin = ['mysql=8.4.8']
        with self.assertRaisesRegex(ValueError, 'reason'):
            self.prepare()
        self.args.reason = 'Explicit fixture project pin'
        self.prepare(); self.seal()
        self.assertEqual(pre.require_preflight('resource')['pins'], {'mysql':'8.4.8'})

    def test_default_scope_and_metadata(self):
        self.assertNotIn('migration', pre.outputs(pre.DEFAULT_OUTPUTS))
        self.assertEqual(pre.outputs('arch'), ['arch'])
        with self.assertRaises(ValueError):
            pre.outputs('unknown')
        meta = _extract_metadata('https://pdpublic.mingdao.com/private-deployment/offline/minio-example.tar.gz '
                                 'mingdaoyun-hap:7.3.1 mysql-8.4.8 istio-1.29.2 RELEASE.2025-04-22T22-12-26Z')
        self.assertEqual(len(meta['package_urls']), 1)
        self.assertEqual(meta['versions']['hap'], ['7.3.1'])
        self.assertEqual(meta['versions']['mysql'], ['8.4.8'])
        self.assertEqual(meta['versions']['istio'], ['1.29.2'])


if __name__ == '__main__':
    unittest.main()
