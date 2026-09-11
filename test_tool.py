import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("local_tool",HERE/"tool.py")
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)

class ToolTests(unittest.TestCase):
    def setUp(self):
        self.cases=json.loads((HERE/"examples/cases.json").read_text())
        self.payload=copy.deepcopy(self.cases[0]['input'])
        self.data=self.payload['data']
    def check_case(self,name):
        case=next(c for c in self.cases if c['name']==name)
        actual=tool.analyze(case['input'])
        self.assertTrue(tool.matches(actual,case['expected']),repr(actual))
    def test_positive(self): self.check_case('positive')
    def test_negative(self): self.check_case('negative')
    def test_unknown(self): self.check_case('unknown')
    def test_frozen_oracles(self):
        manifest=json.loads((HERE/'examples/frozen.json').read_text())
        for name,digest in manifest['sha256'].items():
            self.assertEqual(hashlib.sha256((HERE/'examples'/name).read_bytes()).hexdigest(),digest)
    def test_deterministic_immutable(self):
        before=copy.deepcopy(self.payload);a=tool.analyze(self.payload);b=tool.analyze(self.payload)
        self.assertEqual(a,b);self.assertEqual(before,self.payload)
    def invoke(self,content,expected=None):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);(td/'input.json').write_text(content)
            cmd=[sys.executable,str(HERE/'tool.py'),'--input',str(td/'input.json'),'--output',str(td/'output.json')]
            if expected is not None:
                (td/'expected.json').write_text(json.dumps(expected));cmd+=['--expect',str(td/'expected.json')]
            return subprocess.run(cmd,capture_output=True,text=True)
    def test_cli_example_exit_zero(self):
        self.assertEqual(self.invoke(json.dumps(self.payload),self.cases[0]['expected']).returncode,0)
    def test_configured_mismatch_exit_one(self):
        self.assertEqual(self.invoke(json.dumps(self.payload),{'status':'INTENTIONALLY_WRONG'}).returncode,1)
    def test_malformed_exit_two(self):
        r=self.invoke('{');self.assertEqual(r.returncode,2);self.assertIn('invalid input:',r.stderr)
    def test_oversize_exit_two(self): self.assertEqual(self.invoke(' '*1000001).returncode,2)
    def test_unknown_fields_exit_two(self):
        self.data['unknown_extension']=True
        self.assertEqual(self.invoke(json.dumps(self.payload)).returncode,2)
    def test_missing_field_exit_two(self):
        del self.data[next(iter(self.data))]
        self.assertEqual(self.invoke(json.dumps(self.payload)).returncode,2)
    def test_rejection_preserves_owner(self):
        self.data['decision']['accepted']=False
        r=tool.analyze(self.payload);self.assertEqual(r['owner'],'agent');self.assertEqual(r['resume_steps'],[])
    def test_obsolete_decision_refused(self):
        self.data['decision']['packet_version']='old'
        self.assertIn('obsolete_decision',tool.analyze(self.payload)['issues'])
    def test_unowned_obligation_refused(self):
        self.data['obligations'][0]['owner']=None
        self.assertIn('unowned_obligation:o1',tool.analyze(self.payload)['issues'])

if __name__ == "__main__": unittest.main()
