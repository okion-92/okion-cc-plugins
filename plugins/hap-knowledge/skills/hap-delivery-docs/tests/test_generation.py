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
                 for url in pre.source_urls('lite', selected, 'mingdao').values()}
        bundle = self.dir/'bundle.json'; bundle.write_text(json.dumps(pages),encoding='utf-8')
        report = self.dir/'report.json'
        args = argparse.Namespace(version='lite', outputs=selected, brand='mingdao', input=str(self.input),
            architecture=str(self.arch) if custom else None, bundle=str(bundle), source=[], pin=[], reason='',
            allow_offline=False, report=str(report))
        with redirect_stdout(io.StringIO()):
            pre.prepare(args)
            pre.seal(argparse.Namespace(report=str(report),note='Reviewed synthetic test fixture',allow_offline=False))
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


if __name__ == '__main__':
    unittest.main()
