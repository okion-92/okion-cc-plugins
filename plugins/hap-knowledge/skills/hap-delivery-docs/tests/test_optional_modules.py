"""Input defaults, dependency boundaries and reviewed content binding."""
import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import optional_modules as mod
import source_preflight as pre


class OptionalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hap-optional-')
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.input = self.dir/'input.xlsx'

    def workbook(self, rows=()):
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = '可选模块'
        for i, row in enumerate(rows,4):
            for j, value in enumerate(row,1): ws.cell(i,j,value)
        wb.save(self.input)

    def test_intake_template_has_all_defaults_off_and_last_custom_sheet(self):
        result = subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/make_input_template.py'),str(self.input)],
                                capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        wb = openpyxl.load_workbook(self.input)
        ws = wb['⑦ 可选模块']
        self.assertEqual({ws.cell(r,1).value for r in range(4,ws.max_row+1)},set(mod.MODULES))
        self.assertTrue(all(ws.cell(r,3).value=='无' for r in range(4,ws.max_row+1)))
        self.assertEqual(len(ws.data_validations.dataValidation),len(mod.MODULES))
        self.assertIn('自定义项描述',wb.sheetnames[-1])
        self.assertEqual(mod.read_modules(self.input),{})
        self.assertFalse(any('公有云' in str(c.value) for s in wb for row in s for c in row))

    def test_old_workbook_and_empty_choices_preserve_default(self):
        wb = openpyxl.Workbook(); wb.save(self.input)
        self.assertEqual(mod.read_modules(self.input),{})
        self.workbook([['milvus','Milvus',None],['etcd','etcd','无']])
        self.assertEqual(mod.read_modules(self.input),{})

    def test_invalid_modes_missing_nodes_and_implicit_dependencies_rejected(self):
        for rows, message in [([['unknown','unknown','启用']],'未知'),
                              ([['milvus','Milvus','yes','node']],'无效'),
                              ([['etcd','etcd','单节点']],'节点'),
                              ([['milvus','Milvus','启用','node']],'依赖'),
                              ([['mongodb83','MongoDB','单节点副本集','node']],'适用性'),
                              ([['etcd','etcd','无'],['etcd','etcd','无']],'重复')]:
            with self.subTest(rows=rows):
                self.workbook(rows)
                with self.assertRaisesRegex(ValueError,message): mod.read_modules(self.input)

    def test_current_source_routes_do_not_enable_other_modes(self):
        for key, spec in mod.MODULES.items():
            for mode in spec[1]:
                with self.subTest(key=key,mode=mode):
                    urls = mod.source_urls({key:{'mode':mode}})
                    self.assertTrue(urls)
                    self.assertTrue(all(k.startswith('optional_'+key+'_') for k in urls))
        docker = mod.source_urls({'victorialogs':{'mode':'Docker'}})
        self.assertTrue(any('victorialogs-docker' in u for u in docker.values()))
        self.assertFalse(any('victorialogs-promtail' in u for u in docker.values()))
        urls = pre.source_urls('std',['deploy'],'mingdao',{'mysql_mode':{'mode':'主从'}})
        self.assertNotIn('mysql_mgr',urls)
        self.assertIn('optional_mysql_mode_1',urls)
        default = pre.source_urls('std',['deploy'],'mingdao')
        self.assertFalse(any(k.startswith('optional_') for k in default))

    def test_selected_content_cannot_be_missing_extra_or_mode_mismatched(self):
        record = {'modules':{'etcd':{'mode':'单节点','nodes':'node'}},'outputs':['deploy']}
        with self.assertRaisesRegex(ValueError,'完整|JSON'): mod.validate_content(record,None)
        path = self.dir/'modules.json'
        content = {'schema':1,'modules':{'etcd':{'mode':'集群','nodes':'node','sections':{}}}}
        path.write_text(json.dumps(content),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'模式'): mod.validate_content(record,path)
        content['modules']['etcd'].update(mode='单节点',review='Fixture review',sections={'deploy':'https://example.invalid/'})
        path.write_text(json.dumps(content),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'正文'): mod.validate_content(record,path)

    def test_variants_require_whole_document_and_credentials(self):
        record = {'modules':{'mysql_mode':{'mode':'主从','nodes':'node'}},'outputs':['deploy','cred']}
        section = 'A synthetic full operation and validation description, with commands:\n```sh\nfixture-check\n```'
        content = {'schema':1,'modules':{'mysql_mode':{'mode':'主从','nodes':'node','review':'Fixture review',
                    'sections':{'deploy':section},'credentials':[]}}}
        path = self.dir/'content.json'; path.write_text(json.dumps(content),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'完整替代文档'): mod.validate_content(record,path)
        content['documents'] = {'deploy':section}
        path.write_text(json.dumps(content),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'完整凭据'): mod.validate_content(record,path)

    def test_preflight_requires_content_and_detects_changed_content(self):
        self.workbook([['etcd','etcd','单节点','node','']])
        report = self.dir/'report.json'
        pages = {url:{'content':'Synthetic preflight source text; fixture only, not a real official-page verification.',
                      'links':[],'fetched_at':pre.now()}
                 for url in pre.source_urls('lite',['ops'],'mingdao',mod.read_modules(self.input)).values()}
        pages[mod.BASE+mod.INSTALL+'etcd/']['content'] += ' mingdaoyun-etcd-linux-amd64-v3.6.11.tar.gz'
        bundle = self.dir/'bundle.json'; bundle.write_text(json.dumps(pages),encoding='utf-8')
        args = argparse.Namespace(version='lite',outputs='ops',brand='mingdao',input=str(self.input),architecture=None,
            bundle=str(bundle),source=[],pin=[],reason='',allow_offline=False,report=str(report))
        with patch.object(pre,'fetch',side_effect=OSError('No network in tests')), redirect_stdout(io.StringIO()):
            pre.prepare(args)
            review = argparse.Namespace(report=str(report),note='Synthetic content review',allow_offline=False,module_content=None)
            with self.assertRaisesRegex(ValueError,'JSON'): pre.seal(review)
            path = self.dir/'content.json'
            path.write_text(json.dumps({'schema':1,'modules':{'etcd':{'mode':'单节点','nodes':'node',
                'review':'Synthetic fixture reviewed','sections':{'ops':'Complete synthetic maintenance and backup instructions, with recovery and verification checks. etcd-3.6.10'}}}}),encoding='utf-8')
            review.module_content = str(path)
            with self.assertRaisesRegex(ValueError,'版本落后'): pre.seal(review)
            path.write_text(path.read_text(encoding='utf-8').replace('etcd-3.6.10','etcd-3.6.11'),encoding='utf-8')
            pre.seal(review)
            with patch.dict('os.environ',HAP_PREFLIGHT_REPORT=str(report),HAP_DELIVERY_INPUT=str(self.input)):
                self.assertEqual(pre.require_preflight('ops')['modules']['etcd']['mode'],'单节点')
                path.write_text('{}',encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'内容变化'): pre.require_preflight('ops')


if __name__ == '__main__':
    unittest.main()
