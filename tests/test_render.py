#!/usr/bin/env python3
import json,os,pathlib,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parent.parent
class RendererTests(unittest.TestCase):
 def invoke(self,documents=None,options=None,raw=None):
  with tempfile.TemporaryDirectory(prefix='mdx protocol café ') as folder:
   path=pathlib.Path(folder);request={'version':1,'documents':documents or [{'id':'one','source':'# Hello','path':None,'dependencies':[]}],'options':options or {'policy':'trusted'}}
   (path/'request.json').write_text(raw if raw is not None else json.dumps(request))
   env=os.environ.copy();env.setdefault('MDX_NODE_MODULES','/usr/local/lib/node_modules')
   run=subprocess.run(['node',str(ROOT/'renderer/cli.mjs'),'--request','request.json','--response','response.json'],cwd=path,env=env,capture_output=True,text=True,timeout=20)
   return run,json.loads((path/'response.json').read_text())
 def test_protocol(self):
  run,response=self.invoke();self.assertEqual(response['version'],1);self.assertEqual(response['results'][0]['id'],'one')
 def test_source_bound(self):
  run,response=self.invoke([{'id':'large','source':'x'*262145,'path':None,'dependencies':[]}]);self.assertNotEqual(run.returncode,0);self.assertIn('limit',response['diagnostics'][0]['message'])
 def test_duplicate(self):
  doc={'id':'duplicate','source':'Hi','path':None,'dependencies':[]};run,response=self.invoke([doc,doc]);self.assertNotEqual(run.returncode,0);self.assertEqual(response['diagnostics'][0]['stage'],'transport')
 def test_policy(self):
  run,response=self.invoke(options={'policy':'untrusted'});self.assertNotEqual(run.returncode,0);self.assertIn('explicit policy',response['diagnostics'][0]['message'])
 def test_bad_json(self):
  run,response=self.invoke(raw='{');self.assertNotEqual(run.returncode,0);self.assertEqual(response['diagnostics'][0]['stage'],'transport')
 def test_timeout(self):
  run,response=self.invoke(options={'policy':'trusted','timeoutMs':1});self.assertNotEqual(run.returncode,0);self.assertEqual(response['diagnostics'][0]['code'],'timeout')
 def test_unicode_transport(self):
  run,response=self.invoke([{'id':'quotes " and café','source':'# café\n\nQuotes " and $[literal]','path':None,'dependencies':[]}]);self.assertEqual(response['results'][0]['id'],'quotes " and café')
if __name__=='__main__':unittest.main()
