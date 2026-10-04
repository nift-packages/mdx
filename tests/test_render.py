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
 def test_installed_nift_facade(self):
  nift=os.environ.get('NIFT','/home/nick/Repositories/nift/nift/nift')
  with tempfile.TemporaryDirectory(prefix='mdx-installed-') as folder:
   path=pathlib.Path(folder);env=os.environ.copy();env.setdefault('MDX_NODE_MODULES','/usr/local/lib/node_modules')
   subprocess.run([nift,'add',str(ROOT)],cwd=path,env=env,capture_output=True,text=True,check=True)
   (path/'.nift/mdx-render.json').write_text(json.dumps({'policy':'trusted'}))
   (path/'page.mdx').write_text('# Prepared\n\nHello.')
   (path/'render.f').write_text('@import("mdx")\nmdx.prepare([mdx.input("page.mdx")])\nprint(mdx.html(mdx.input("page.mdx")))\nprint(mdx.html(mdx.parse("# Inline")))\n')
   run=subprocess.run([nift,'render.f'],cwd=path,env=env,capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stderr);self.assertIn('mdx-prepared',run.stdout);self.assertIn('mdx-inline',run.stdout)
   blocked=subprocess.run([nift,'render.f','--no-process'],cwd=path,env=env,capture_output=True,text=True);self.assertNotEqual(blocked.returncode,0);self.assertIn('execution disabled',blocked.stderr)
   (path/'page.mdx').write_text('# Changed')
   (path/'stale.f').write_text('@import("mdx")\nprint(mdx.html(mdx.input("page.mdx")))\n')
   stale=subprocess.run([nift,'stale.f'],cwd=path,env=env,capture_output=True,text=True);self.assertNotEqual(stale.returncode,0);self.assertIn('stale',stale.stderr)
 def test_protocol(self):
  run,response=self.invoke();self.assertEqual(response['version'],1);self.assertEqual(response['results'][0]['id'],'one');self.assertTrue(response['ok']);self.assertIn('<h1 id="mdx-hello">',response['results'][0]['html'])
 def test_markdown_and_plain_output(self):
  source='# Example\n\nA **paragraph** with [link](https://example.org) and `inline`.\n\n- One\n  - Nested\n\n```js\nconsole.log("<escaped>")\n```\n\n![caption](image.png)'
  run,response=self.invoke([{'id':'markdown','source':source,'path':None,'dependencies':[]}]);self.assertEqual(run.returncode,0)
  html=response['results'][0]['html']
  for fragment in ['<strong>paragraph</strong>','<a href="https://example.org">','<code>inline</code>','<ul>','language-js','&lt;escaped&gt;','alt="caption"']:self.assertIn(fragment,html)
  for fragment in ['<script','hydrateRoot','react-dom','jsx-runtime']:self.assertNotIn(fragment,html)
 def test_mixed_batch_errors(self):
  run,response=self.invoke([{'id':name,'source':source,'path':None,'dependencies':[]} for name,source in [('good','# Good'),('unknown','<Unknown />'),('malformed','<Aside')]])
  self.assertNotEqual(run.returncode,0);self.assertEqual([r['ok'] for r in response['results']],[True,False,False]);self.assertEqual(response['results'][1]['diagnostics'][0]['stage'],'render')
 def test_trusted_expression_and_no_implicit_execution(self):
  document={'id':'expression','source':'{1 + 2}','path':None,'dependencies':[]}
  run,response=self.invoke([document]);self.assertEqual(run.returncode,0);self.assertIn('3',response['results'][0]['html'])
  run,response=self.invoke([document],options={'timeoutMs':1000});self.assertNotEqual(run.returncode,0);self.assertIn('explicit policy',response['diagnostics'][0]['message'])
 def test_trusted_infinite_expression_deadline(self):
  run,response=self.invoke([{'id':'loop','source':'{(() => { while(true) {} })()}','path':None,'dependencies':[]}],options={'policy':'trusted','timeoutMs':700});self.assertNotEqual(run.returncode,0);self.assertEqual(response['diagnostics'][0]['code'],'timeout')
 def test_frontmatter_and_original_locations(self):
  for newline in ['\n','\r\n','\r']:
   prefix=newline.join(['---','title: café','---','']);source=prefix+'# Body'
   front={'present':True,'source':prefix,'end':{'offset':len(prefix.encode())}}
   run,response=self.invoke([{'id':'front','source':source,'path':'article.mdx','dependencies':[],'frontmatter':front}]);self.assertEqual(run.returncode,0);html=response['results'][0]['html'];self.assertIn('Body',html);self.assertNotIn('title:',html)
  run,response=self.invoke([{'id':'error','source':'---\ntitle: Example\n---\n<Aside','path':'article.mdx','dependencies':[]}]);self.assertNotEqual(run.returncode,0);self.assertEqual(response['results'][0]['diagnostics'][0]['line'],4)
 def test_empty_and_unclosed_frontmatter(self):
  run,response=self.invoke([{'id':'empty','source':'---\n---\n','path':None,'dependencies':[]}]);self.assertEqual(run.returncode,0);self.assertEqual(response['results'][0]['html'],'')
  run,response=self.invoke([{'id':'unclosed','source':'---\ntitle: x','path':None,'dependencies':[]}]);self.assertNotEqual(run.returncode,0);self.assertIn('Unclosed frontmatter',response['results'][0]['diagnostics'][0]['message'])
 def test_invalid_frontmatter_boundary(self):
  run,response=self.invoke([{'id':'front','source':'# Body','path':None,'dependencies':[],'frontmatter':{'present':True,'source':'wrong','end':{'offset':2}}}]);self.assertNotEqual(run.returncode,0);self.assertIn('frontmatter boundary',response['results'][0]['diagnostics'][0]['message'])
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
