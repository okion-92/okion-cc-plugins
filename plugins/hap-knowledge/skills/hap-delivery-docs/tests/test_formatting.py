"""Verify new source-based chapter text uses the unchanged Word layout pipeline."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import optional_modules as mod

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


class FormattingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hap-layout-qa-')
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)

    def test_new_chapters_keep_cover_styles_tables_and_code_format(self):
        base = self.dir/'base.md'
        base.write_text('# 原有部署章节\n\n保留原有正文与中文字体回退。\n\n'
            '| 组件 | 端口 |\n| --- | --- |\n| HAP | 8880 |\n\n'
            '```sh\n# 原有命令\nkubectl get nodes -o wide\n```\n\n'
            '# 十三、上线验证与验收\n\n核对实际结果后填写验收记录。\n',encoding='utf-8')
        # Paraphrased source-based excerpt for layout QA, not a deployable project runbook.
        section = ('# 独立 etcd 配置与验证\n\n'
            '根据实际节点配置客户端与集群通信地址；使用独立数据目录和运行账号。\n\n'
            '| 配置项 | 实际值 |\n| --- | --- |\n| data-dir | /data/etcd |\n\n'
            '```yaml\n# 此注释应保留为代码\nname: etcd\ndata-dir: /data/etcd\n'
            'log-outputs:\n  - /data/logs/etcd/etcd.log\n```\n\n'
            '## 启动和检查\n\n'
            '```sh\nsystemctl daemon-reload\nsystemctl start etcd\nsystemctl enable etcd\n'
            'systemctl status etcd --no-pager\njournalctl -u etcd -n 100 --no-pager\n```\n\n'
            '来源：https://docs-pdop.mingdao.com/deployment/cluster/installation/etcd/\n')
        content = {'modules':{'etcd':{'mode':'单节点','sections':{'deploy':section}}}}
        mod.check_markdown(section,'etcd/deploy',commands=True)
        with patch.object(mod,'runtime',return_value=({},content)):
            expanded = Path(mod.materialize_markdown(base,'deploy'))
        result = expanded.read_text(encoding='utf-8')
        self.assertLess(result.index('# 可选模块'),result.index('# 十三、上线验证与验收'))
        self.assertIn('## 独立 etcd 配置与验证',result)
        self.assertIn('\n# 此注释应保留为代码\n',result)
        self.paths = []
        for source,name in ((base,'original.docx'),(expanded,'expanded.docx')):
            target = self.dir/name
            subprocess.run(['node',str(ROOT/'scripts/render_deploy.js'),str(source),str(target),'格式核验样张'],
                           cwd=ROOT,check=True,capture_output=True)
            subprocess.run([sys.executable,str(ROOT/'scripts/inject_cover.py'),str(target),'格式核验样张',
                            'HAP Format Verification','2026/11/20'],check=True,capture_output=True)
            self.paths.append(target)
        with zipfile.ZipFile(self.paths[0]) as old, zipfile.ZipFile(self.paths[1]) as new:
            for part in ('word/styles.xml','word/header1.xml','word/footer1.xml'):
                self.assertEqual(old.read(part),new.read(part),part)
            a = ET.fromstring(old.read('word/document.xml')); b = ET.fromstring(new.read('word/document.xml'))
        abody = a.find(W+'body'); bbody = b.find(W+'body')
        self.assertEqual(ET.tostring(abody.find(W+'sectPr')),ET.tostring(bbody.find(W+'sectPr')))
        for x,y in zip(list(abody)[:10],list(bbody)[:10]):
            self.assertEqual(ET.tostring(x),ET.tostring(y),'cover or retained opening content changed')
        tables = list(b.iter(W+'tbl'))
        original_tables = list(a.iter(W+'tbl'))
        self.assertEqual(len(tables),len(original_tables)+3)
        for old_table,new_table in zip(original_tables,tables):
            self.assertEqual(ET.tostring(old_table),ET.tostring(new_table))
        for table in tables[len(original_tables):]:
            self.assertEqual(table.find(W+'tblPr/'+W+'tblW').get(W+'w'),'9360')
        code_runs = [r for r in b.iter(W+'r') if r.find(W+'rPr/'+W+'rFonts') is not None
                     and r.find(W+'rPr/'+W+'rFonts').get(W+'ascii')=='Consolas']
        self.assertIn('  - /data/logs/etcd/etcd.log',[''.join(r.itertext()) for r in code_runs])
        self.assertGreater(len(code_runs),8)
        for run in code_runs:
            self.assertEqual(run.find(W+'rPr/'+W+'sz').get(W+'val'),'17')
            self.assertEqual(run.find(W+'rPr/'+W+'color').get(W+'val'),'1A6B33')

    def test_malformed_blocks_are_rejected_before_rendering(self):
        with self.assertRaisesRegex(ValueError,'未闭合'):
            mod.check_markdown('完整步骤和配置说明 '*10+'\n```yaml\nname: etcd','test',commands=True)
        with self.assertRaisesRegex(ValueError,'控制字符'):
            mod.check_markdown('完整步骤和配置说明 '*10+'\x00','test')


if __name__ == '__main__':
    unittest.main()
