"""Optional intake, source routing and reviewed project chapters; absent means disabled."""
import json
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import openpyxl

BASE = 'https://docs-pdop.mingdao.com/'
INSTALL = 'deployment/cluster/installation/'
MONITOR = INSTALL + 'monitor/'
# URLs are discovery seeds. Read current pages and applicability before writing chapters.
MODULES = {
    'etcd': ('独立 etcd', ['单节点', '集群', '使用现有'], {
        '单节点': [INSTALL+'etcd/'], '集群': [INSTALL+'etcd/etcd-cluster/'],
        '使用现有': [INSTALL+'etcd/']}, 'etcd'),
    'milvus': ('Milvus 向量检索', ['启用'], {'启用': [INSTALL+'milvus/']}, 'Milvus'),
    'compute': ('专属算力', ['启用'], {'启用': ['deployment/computing/', 'deployment/computing/deploy/']}, '专属算力'),
    'hdp': ('HDP 独立服务', ['启用'], {'启用': ['deployment/hdp/deploy/']}, 'HDP'),
    'alerts': ('监控告警通知', ['启用'], {'启用': [MONITOR+'alert/']}, 'Alertmanager'),
    'kibana': ('Kibana', ['启用'], {'启用': [MONITOR+'kibana/']}, 'Kibana'),
    'victorialogs': ('VictoriaLogs 慢查询日志', ['二进制', 'Docker'], {
        '二进制': [MONITOR+'victorialogs/', MONITOR+'victorialogs/mongodb-log-cut/', MONITOR+'victorialogs/victorialogs-promtail/'],
        'Docker': [MONITOR+'victorialogs/', MONITOR+'victorialogs/mongodb-log-cut/', MONITOR+'victorialogs/victorialogs-docker/']}, 'VictoriaLogs'),
    'mysql_mode': ('MySQL 替代部署模式', ['主从'], {'主从': [INSTALL+'mysql/mysql-8.4/master-slave-8.4/']}, 'MySQL'),
    'redis_mode': ('Redis 替代部署模式', ['主从', '主从+Keepalived（EOL）'], {
        '主从': [INSTALL+'redis/master-slave/'],
        '主从+Keepalived（EOL）': [INSTALL+'redis/master-slave/', INSTALL+'redis/master-slave-keepalived/']}, 'Redis'),
    'mongodb83': ('MongoDB 8.3 副本集', ['单节点副本集', '三节点副本集'], {
        '单节点副本集': [INSTALL+'mongodb/8.3/standalone/'],
        '三节点副本集': [INSTALL+'mongodb/8.3/replica-set/']}, 'MongoDB'),
    'implementation_plan': ('组件实施进度表', ['启用'], {'启用': ['deployment/guide/']}, ''),
    'functional_validation': ('业务功能验证记录', ['启用'], {'启用': ['deployment/guide/']}, ''),
}
VARIANTS = {'mysql_mode', 'redis_mode', 'mongodb83'}
TEXT_OUTPUTS = {'deploy', 'ops', 'faq', 'resource', 'checklist'}


def read_modules(path):
    if not path:
        return {}
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        sheets = [s for s in wb if '可选模块' in s.title]
        if not sheets:
            return {}  # Old workbooks retain their existing behavior.
        if len(sheets) != 1:
            raise ValueError('入参只允许一个可选模块 Sheet')
        selected, seen = {}, set()
        for row in sheets[0].iter_rows(min_row=4, values_only=True):
            key = str(row[0] or '').strip()
            if not key:
                continue
            if key not in MODULES or key in seen:
                raise ValueError('未知或重复的可选模块: '+key)
            seen.add(key)
            mode = str(row[2] or '无').strip() if len(row) > 2 else '无'
            if mode == '无':
                continue
            if mode not in MODULES[key][1]:
                raise ValueError('可选模块模式无效: '+key)
            nodes = str(row[3] or '').strip() if len(row) > 3 else ''
            notes = str(row[4] or '').strip() if len(row) > 4 else ''
            if MODULES[key][3] and not nodes:
                raise ValueError(MODULES[key][0]+'已启用，请填写节点/访问端点；不得推定实际节点')
            if (key == 'mongodb83' or 'EOL' in mode) and not notes:
                raise ValueError(MODULES[key][0]+'请填写适用性/版本兼容说明')
            selected[key] = {'mode': mode, 'nodes': nodes, 'notes': notes}
        if 'milvus' in selected and 'etcd' not in selected:
            raise ValueError('Milvus 依赖独立 etcd；请显式选择 etcd 单节点/集群/使用现有，并填写端点')
        return selected
    finally:
        wb.close()


def source_urls(modules):
    return {'optional_%s_%d' % (key, i): BASE+path
            for key, choice in modules.items()
            for i, path in enumerate(MODULES[key][2][choice['mode']], 1)}


def validate_selections(modules):
    if set(modules) - MODULES.keys():
        raise ValueError('来源记录包含未知可选模块')
    for key, item in modules.items():
        if item.get('mode') not in MODULES[key][1]:
            raise ValueError('来源记录包含无效可选模式: '+key)


def check_markdown(text, key, commands=False):
    if not isinstance(text, str) or len(text.strip()) < 40 or re.search(r'\bTODO\b|\bTBD\b|待补充|稍后补充', text, re.I):
        raise ValueError('可选内容缺少完整正文: '+key)
    if commands and '```' not in text:
        raise ValueError('可选部署章节必须包含已核对的命令/配置代码块: '+key)


def validate_content(record, path):
    modules = record.get('modules', {})
    technical = {k for k in modules if MODULES[k][3]}
    if not technical:
        return None
    if not path:
        raise ValueError('已启用技术模块：按 reference/optional-modules.md 编写本项目内容 JSON，再 seal --module-content；不能只添加链接')
    content = json.loads(Path(path).read_text(encoding='utf-8'))
    if content.get('schema') != 1 or set(content.get('modules', {})) != technical:
        raise ValueError('项目内容必须且只能包含入参启用的技术模块')
    selected = set(record['outputs'])
    for key in technical:
        item = content['modules'][key]
        if item.get('mode') != modules[key]['mode']:
            raise ValueError('项目章节模式与入参不一致: '+key)
        if item.get('nodes') != modules[key]['nodes']:
            raise ValueError('项目章节节点与入参不一致: '+key)
        sections = item.get('sections', {})
        if set(sections) - TEXT_OUTPUTS:
            raise ValueError('未知可选章节类型: '+key)
        for kind in selected & TEXT_OUTPUTS:
            if key in VARIANTS and kind != 'checklist':
                continue  # The full replacement below already contains this database mode.
            check_markdown(sections.get(kind), key+'/'+kind, commands=(kind == 'deploy' and modules[key]['mode'] != '使用现有'))
        if not item.get('review'):
            raise ValueError('缺少依赖、网络、适用性及验证步骤核对记录: '+key)
        if 'cred' in selected:
            if not isinstance(item.get('credentials'), list):
                raise ValueError('模块凭据必须提供列表，无新增凭据时用空列表: '+key)
            for row in item['credentials']:
                credential_tuple(row, key)
    documents = content.get('documents', {})
    if set(documents) - (TEXT_OUTPUTS | {'migration'}):
        raise ValueError('项目内容包含未知文档类型')
    # Replacing a database topology affects the whole document, not just an appendix.
    if technical & VARIANTS:
        for kind in selected & {'deploy', 'ops', 'migration', 'faq', 'resource'}:
            check_markdown(documents.get(kind), '完整替代文档/'+kind, commands=kind == 'deploy')
        if 'cred' in selected:
            if not content.get('replacement_credentials') or not isinstance(content.get('replacement_constraints'), list):
                raise ValueError('数据库模式替换需完整凭据和一致性约束，避免保留原 MGR/哨兵口径')
            for row in content['replacement_credentials']:
                credential_tuple(row)
            if any(not isinstance(c, list) or len(c) != 4 for c in content['replacement_constraints']):
                raise ValueError('凭据一致性约束必须为四列列表')
    return content


def credential_tuple(row, module=None):
    fields = ('component', 'node', 'port', 'user', 'key', 'placeholder', 'config', 'chapter', 'dependency')
    if not isinstance(row, dict) or set(row) - set(fields) - {'input_key'} or any(f not in row for f in fields):
        raise ValueError('凭据行必须提供规定字段；实际密码只从入参凭据页读取')
    if any(not isinstance(row[f], str) for f in fields) or not isinstance(row.get('input_key', ''), str):
        raise ValueError('凭据字段必须是字符串')
    if module and not row['key'].startswith('可选/'+module+'/'):
        raise ValueError('模块凭据 key 必须带可选模块前缀: '+module)
    return tuple(row[f] for f in fields)


def validate_architecture(modules, path, selected):
    if 'arch' not in selected or not any(MODULES[k][3] for k in modules):
        return
    if not path:
        raise ValueError('已选技术模块需制作反映实际节点、依赖与访问方向的项目 SVG，并传 --architecture')
    text = ' '.join(ET.parse(path).getroot().itertext())
    for key in modules:
        label = MODULES[key][3]
        if label and label.lower() not in text.lower():
            raise ValueError('项目架构图缺少已选模块: '+label)


def runtime():
    path = os.environ.get('HAP_PREFLIGHT_REPORT')
    record = json.loads(Path(path).read_text(encoding='utf-8')) if path else {}
    binding = record.get('module_content')
    return record, json.loads(Path(binding['file']).read_text(encoding='utf-8')) if binding else {}


def materialize_markdown(path, kind):
    record, content = runtime()
    if not content:
        return path
    original = Path(path)
    body = content.get('documents', {}).get(kind, original.read_text(encoding='utf-8'))
    for key, item in content.get('modules', {}).items():
        section = item.get('sections', {}).get(kind)
        if section and not (key in VARIANTS and kind in content.get('documents', {})):
            body += '\n\n# 可选模块：'+MODULES[key][0]+'（'+item['mode']+'）\n\n'+section+'\n'
    work = original.parent if original.parent.name == '_work' else original.parent/'_work'
    work.mkdir(exist_ok=True)
    target = work/(original.stem+'_optional.md')
    target.write_text(body, encoding='utf-8')
    return str(target)


def configure_credentials(rows, constraints):
    _, content = runtime()
    rows = [credential_tuple(r) for r in content['replacement_credentials']] if 'replacement_credentials' in content else rows
    constraints = content.get('replacement_constraints', constraints)
    for key, item in content.get('modules', {}).items():
        rows += [credential_tuple(r, key) for r in item.get('credentials', [])]
    return rows, constraints


def credential_values():
    path = os.environ.get('HAP_DELIVERY_INPUT')
    if not path:
        return {}
    _, content = runtime()
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        sheet = next(s for s in wb if '凭据清单' in s.title)
        values = {str(r[0]): str(r[4]) for r in sheet.iter_rows(min_row=4, values_only=True)
                  if r[0] and len(r) > 4 and r[4] is not None}
        rows = list(content.get('replacement_credentials', []))
        for item in content.get('modules', {}).values():
            rows.extend(item.get('credentials', []))
        return {row['key']: values[row['input_key']] for row in rows if row.get('input_key') in values}
    finally:
        wb.close()


def generate_records(outdir, selected, modules):
    tasks = []
    if 'implementation_plan' in modules and 'deploy' in selected:
        core = ['Docker', 'MongoDB', 'MySQL', 'Redis', 'Kafka', 'Elasticsearch', 'MinIO', 'File', 'Kubernetes', 'Istio', 'HAP 微服务', 'Flink', 'Nginx', 'Prometheus', 'Grafana']
        core += [MODULES[k][0]+'（'+v['mode']+'）' for k, v in modules.items() if MODULES[k][3] and k not in VARIANTS]
        tasks.append(('HAP组件实施进度表.xlsx', '实施进度', ['组件', '负责人', '开始时间', '计划完成时间', '实际完成时间', '组件验证结果', '备注'], core))
    if 'functional_validation' in modules and set(selected) & {'deploy', 'checklist'}:
        features = ['动态发布', '任务创建', '日程创建', '附件上传', '附件预览', '附件下载', '应用创建', '工作表创建', '工作表数据新增', '工作表数据修改', '工作表数据删除', '工作流创建', '工作流启动', '工作流编辑', '工作流触发', '工作流停止', '工作流删除', '数据源添加（按项目功能范围）', '同步任务创建（按项目功能范围）']
        features += [MODULES[k][0]+'专项验证' for k in modules if MODULES[k][3]]
        tasks.append(('HAP业务功能验证记录.xlsx', '功能验证', ['功能点', '验证操作', '预期结果', '实际结果', '附件/截图', '备注', '验证人', '验证日期'], features))
    from openpyxl.styles import Font, PatternFill, Alignment
    for filename, title, headers, entries in tasks:
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = title
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True, color='FFFFFF'); cell.fill = PatternFill('solid', fgColor='1E5BA8')
        for entry in entries:
            ws.append([entry]+['']*(len(headers)-1))
        for column in ws.columns:
            ws.column_dimensions[column[0].column_letter].width = 28
            for cell in column:
                cell.alignment = Alignment(vertical='top', wrap_text=True)
        ws.freeze_panes = 'A2'; ws.auto_filter.ref = ws.dimensions
        wb.save(Path(outdir)/filename)
