"""End-to-end output tests with synthetic browser pages, never real customer data."""
import argparse
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import source_preflight as pre
import optional_modules as optional


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hap-generation-test-')
        self.addCleanup(self.temp.cleanup)
        mocked = patch.object(pre, 'fetch', side_effect=OSError('synthetic tests never use the network'))
        mocked.start(); self.addCleanup(mocked.stop)
        self.dir = Path(self.temp.name)
        self.input = self.dir/'input.xlsx'
        wb = openpyxl.Workbook()
        ws = wb.active; ws.title = '项目信息'
        for row, (key, value) in enumerate([('客户名称','A&B 测试'), ('部署版本','集群精简版'),
                                           ('主访问域名','example.invalid'), ('交付日期','2026/11/19')],4):
            ws.cell(row,1,key); ws.cell(row,4,value)
        wb.create_sheet('节点IP规划'); wb.create_sheet('凭据清单')
        wb.create_sheet('自定义项描述')['A1'] = 'TEST FIXTURE ONLY: no customer data'
        wb.save(self.input)
        self.arch = self.dir/'project.svg'
        self.arch.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100"><text x="10" y="50">Project SVG</text></svg>',encoding='utf-8')

    def prepare(self, selected, custom=False):
        pages = {url: {'content':'Synthetic source fixture for generation tests; not a real official-page verification.',
                       'links':[], 'fetched_at':pre.now()}
                 for url in pre.source_urls('lite', selected, 'mingdao', optional.read_modules(self.input)).values()}
        bundle = self.dir/'bundle.json'; bundle.write_text(json.dumps(pages),encoding='utf-8')
        report = self.dir/'report.json'
        args = argparse.Namespace(version='lite', outputs=selected, brand='mingdao', input=str(self.input),
            architecture=str(self.arch) if custom else None, bundle=str(bundle), source=[], pin=[], reason='',
            allow_offline=False, report=str(report))
        with redirect_stdout(io.StringIO()):
            pre.prepare(args)
            pre.seal(argparse.Namespace(report=str(report),note='Reviewed synthetic test fixture',allow_offline=False,
                                       module_content=str(self.content) if hasattr(self, 'content') else None))
        return report

    def generate(self, selected, custom=False):
        report = self.prepare(selected, custom)
        out = self.dir/'out'; out.mkdir()
        unrelated = out/'unrelated.docx'; unrelated.write_bytes(b'preserve this existing file')
        command = [sys.executable,'-X','utf8',str(ROOT/'scripts/gen_from_input.py'),str(self.input),str(out),
                   '--only',selected,'--preflight',str(report)]
        if custom: command += ['--architecture', str(self.arch)]
        result = subprocess.run(command, capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
        self.assertEqual(unrelated.read_bytes(),b'preserve this existing file')
        for path in out.glob('HAP*.docx'):
            with zipfile.ZipFile(path) as archive:
                for name in archive.namelist():
                    if name.endswith('.xml'): ET.fromstring(archive.read(name))
        return out

    def test_only_architecture_and_actual_checklist(self):
        out = self.generate('arch,checklist', custom=True)
        self.assertTrue(list(out.glob('*.svg')) and list(out.glob('*.png')))
        self.assertFalse(any('迁移' in p.name for p in out.iterdir()))
        self.assertFalse(any('场景' in p.name for p in out.iterdir()))
        checklist = next(out.glob('HAP交付清单*.docx'))
        with zipfile.ZipFile(checklist) as archive:
            body = archive.read('word/document.xml').decode('utf-8')
        self.assertIn('架构图.svg',body)
        self.assertNotIn('数据迁移文档',body)
        self.assertNotIn('部署实施文档',body)
        self.assertIn('A&amp;B',body)
        self.assertIn('来源核验时间', (out/'来源核验说明.txt').read_text(encoding='utf-8'))

    def test_migration_can_be_selected_alone(self):
        out = self.generate('migration')
        self.assertEqual(len(list(out.glob('HAP*.docx'))),1)
        self.assertIn('数据迁移', next(out.glob('HAP*.docx')).name)

    def test_direct_generators_fail_before_output_without_preflight(self):
        env = dict(os.environ)
        env.pop('HAP_PREFLIGHT_REPORT',None); env.pop('HAP_DELIVERY_INPUT',None)
        for name in ('deploy','ops','mig','arch','cred','chk','ref'):
            with self.subTest(name=name):
                out = self.dir/name
                args = ['faq'] if name=='ref' else ['lite']
                result = subprocess.run([sys.executable,'-X','utf8',str(ROOT/f'scripts/gen_{name}.py'),*args,str(out)],
                                        env=env,capture_output=True,text=True,encoding='utf-8')
                self.assertNotEqual(result.returncode,0)
                self.assertIn('HAP_PREFLIGHT_REPORT',result.stderr)
                self.assertFalse(out.exists())

    def choose(self, choices):
        wb = openpyxl.load_workbook(self.input)
        ws = wb.create_sheet('可选模块', 3)
        for r, (key, mode) in enumerate(choices.items(), 4):
            for c, val in enumerate([key, optional.MODULES[key][0], mode, 'node.example.invalid', 'Synthetic compatibility fixture'], 1):
                ws.cell(r,c,val)
        creds = wb['凭据清单']
        creds.cell(4,1,'独立 etcd root 密码'); creds.cell(4,5,'SYNTHETIC-secret-do-not-log')
        wb.save(self.input)
        technical = {k:v for k,v in optional.read_modules(self.input).items() if optional.MODULES[k][3]}
        self.arch.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="900" height="500">'+''.join(
            '<text x="10" y="%d">%s</text>'%(30+i*30,optional.MODULES[k][3]) for i,k in enumerate(technical))+'</svg>', encoding='utf-8')
        def section(key, kind):
            return 'OPTIONAL_%s_%s synthetic reviewed content with operating instructions, dependencies and verification.\n```text\nfixture-check\n```'%(key,kind)
        content = {'schema':1, 'modules':{k:{'mode':v['mode'], 'nodes':v['nodes'], 'review':'Synthetic fixture review',
            'sections':{kind:section(k,kind) for kind in optional.TEXT_OUTPUTS}, 'credentials':[]} for k,v in technical.items()}, 'documents':{}}
        if 'etcd' in technical:
            content['modules']['etcd']['credentials'] = [{'component':'独立 etcd','node':'node.example.invalid','port':'2379','user':'root',
                'key':'可选/etcd/root','placeholder':'<强密码>','config':'etcd auth','chapter':'etcd','dependency':'Milvus auth matches',
                'input_key':'独立 etcd root 密码'}]
        if set(technical) & optional.VARIANTS:
            content['documents'] = {kind:section('replacement',kind) for kind in optional.TEXT_OUTPUTS | {'migration'}}
            content['replacement_credentials'] = [{'component':'MySQL','node':'node.example.invalid','port':'3306','user':'root',
                'key':'替代数据库凭据','placeholder':'<强密码>','config':'new database mode','chapter':'Database','dependency':'matches input'}]
            content['replacement_constraints'] = [['A','新模式凭据一致','database and application','<强密码>']]
        self.content = self.dir/'modules.json'
        self.content.write_text(json.dumps(content,ensure_ascii=False),encoding='utf-8')

    def test_optional_modules_render_and_forms_join_actual_checklist(self):
        self.choose({'etcd':'单节点','milvus':'启用','compute':'启用','hdp':'启用','alerts':'启用','kibana':'启用',
                     'victorialogs':'Docker','implementation_plan':'启用','functional_validation':'启用'})
        out = self.generate('deploy,ops,arch,cred,faq,resource,checklist', custom=True)
        self.assertTrue((out/'HAP组件实施进度表.xlsx').is_file())
        self.assertTrue((out/'HAP业务功能验证记录.xlsx').is_file())
        for path in out.glob('HAP*.docx'):
            with zipfile.ZipFile(path) as archive:
                body = archive.read('word/document.xml').decode('utf-8')
            for key in ('etcd','milvus','compute','hdp','alerts','kibana','victorialogs'):
                self.assertIn('OPTIONAL_'+key+'_',body)
            self.assertNotIn('SYNTHETIC-secret-do-not-log',body)
            if '交付清单' in path.name:
                self.assertIn('HAP组件实施进度表.xlsx',body)
                self.assertIn('HAP业务功能验证记录.xlsx',body)
        cred = next(out.glob('*凭据登记表.xlsx'))
        wb = openpyxl.load_workbook(cred)
        vals = [r[7] for r in wb['凭据登记表'].iter_rows(min_row=5,values_only=True) if r[5]=='可选/etcd/root']
        self.assertEqual(vals,['SYNTHETIC-secret-do-not-log'])
        self.assertNotIn('SYNTHETIC-secret-do-not-log',(out/'来源核验说明.txt').read_text(encoding='utf-8'))

    def test_database_variant_replaces_conflicting_baselines(self):
        self.choose({'mysql_mode':'主从','redis_mode':'主从','mongodb83':'单节点副本集'})
        out = self.generate('deploy,ops,migration,arch,cred,faq,resource,checklist', custom=True)
        for path in out.glob('HAP*.docx'):
            if '交付清单' in path.name: continue
            with zipfile.ZipFile(path) as archive: body = archive.read('word/document.xml').decode('utf-8')
            self.assertIn('OPTIONAL_replacement_',body)
            self.assertNotIn('group_replication',body)
            self.assertNotIn('sentinel get-master',body)
        wb = openpyxl.load_workbook(next(out.glob('*凭据登记表.xlsx')))
        keys = [r[5] for r in wb['凭据登记表'].iter_rows(min_row=5,values_only=True)]
        self.assertEqual(keys,['替代数据库凭据'])
        self.assertFalse((out/'HAP组件实施进度表.xlsx').exists())

    def test_forms_respect_only_architecture(self):
        self.choose({'implementation_plan':'启用','functional_validation':'启用'})
        out = self.generate('arch',custom=True)
        self.assertFalse(list(out.glob('*.xlsx')))


if __name__ == '__main__':
    unittest.main()
