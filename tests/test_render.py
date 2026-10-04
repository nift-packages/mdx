#!/usr/bin/env python3
import json,os,pathlib,subprocess,tempfile,unittest,shutil
ROOT=pathlib.Path(__file__).resolve().parent.parent
class RendererTests(unittest.TestCase):
 def invoke(self,documents=None,options=None,raw=None,files=None):
  with tempfile.TemporaryDirectory(prefix='mdx protocol café ') as folder:
   path=pathlib.Path(folder);request={'version':1,'documents':documents or [{'id':'one','source':'# Hello','path':None,'dependencies':[]}],'options':options or {'policy':'trusted'}}
   for name,content in (files or {}).items():
    file=path/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(content)
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
 def test_component_mapping_props_children_fragments(self):
  adapter='export function components({element}) { return {Aside:({type,enabled,count,children})=>element("aside",{"data-type":type,"data-enabled":String(enabled),"data-count":count},children)} }'
  source='<><Aside type="warning" enabled count={1 + 2}><strong>Nested</strong></Aside></>'
  run,response=self.invoke([{'id':'components','source':source,'path':None,'dependencies':[]}],options={'policy':'trusted','components':'components.mjs'},files={'components.mjs':adapter});self.assertEqual(run.returncode,0,run.stderr)
  html=response['results'][0]['html'];self.assertIn('data-count="3"',html);self.assertIn('data-enabled="true"',html);self.assertIn('<strong>Nested</strong>',html);self.assertIn('components.mjs',response['results'][0]['dependencies'])
 def test_component_exception_and_async_refusal(self):
  for adapter,message in [('()=>{throw new Error("adapter failed")}','adapter failed'),('async()=>"bad"','Async component')]:
   run,response=self.invoke([{'id':'components','source':'<Aside />','path':None,'dependencies':[]}],options={'policy':'trusted','components':'components.mjs'},files={'components.mjs':'export default {Aside:'+adapter+'}'});self.assertNotEqual(run.returncode,0);self.assertIn(message,response['results'][0]['diagnostics'][0]['message'])
 def test_transitive_documents_and_inherited_components(self):
  files={'root.mdx':'import Shared from "./shared.mdx"\n\n# Root\n\n<Shared />','shared.mdx':'import Nested from "./nested.mdx"\n\n<Aside>Shared</Aside>\n\n<Nested />','nested.mdx':'import Plain from "./plain.md"\n\n<Plain />','plain.md':'**Plain** Markdown.','components.mjs':'export function components({element}) {return {Aside:({children})=>element("aside",{},children)}}'}
  dependencies=[{'path':name} for name in ['shared.mdx','nested.mdx','plain.md']]
  run,response=self.invoke([{'id':'root','source':files['root.mdx'],'path':'root.mdx','dependencies':dependencies}],options={'policy':'trusted','components':'components.mjs'},files=files);self.assertEqual(run.returncode,0,response)
  html=response['results'][0]['html'];self.assertIn('<aside>Shared</aside>',html);self.assertIn('<strong>Plain</strong>',html)
  self.assertTrue(set(['shared.mdx','nested.mdx','plain.md','components.mjs']).issubset(response['results'][0]['dependencies']))
 def test_unregistered_missing_cycle_and_dynamic_imports(self):
  cases=[('import Shared from "./shared.mdx"\n\n<Shared />',[],{'shared.mdx':'Hi'},'not registered'),('import Shared from "./missing.mdx"\n\n<Shared />',[{'path':'missing.mdx'}],{},'ENOENT'),('import Shared from "./shared.mdx"\n\n<Shared />',[{'path':'shared.mdx'},{'path':'root.mdx'}],{'shared.mdx':'import Root from "./root.mdx"\n\n<Root />','root.mdx':'import Shared from "./shared.mdx"\n\n<Shared />'},'Cyclic'),('{import("./side.mjs")}',[],{},'Dynamic imports')]
  for source,dependencies,files,message in cases:
   run,response=self.invoke([{'id':'root','source':source,'path':'root.mdx','dependencies':dependencies}],files=files);self.assertNotEqual(run.returncode,0);self.assertIn(message,response['results'][0]['diagnostics'][0]['message'])
 def test_named_namespace_document_imports(self):
  for statement,tag in [('import {Label as Shared} from "./shared.mdx"','Shared'),('import * as Shared from "./shared.mdx"','Shared.Label')]:
   run,response=self.invoke([{'id':'root','source':statement+'\n\n<'+tag+' />','path':'root.mdx','dependencies':[{'path':'shared.mdx'}]}],files={'shared.mdx':'export const Label = () => <strong>Named</strong>\n\n# Unused'});self.assertEqual(run.returncode,0,response);self.assertIn('<strong>Named</strong>',response['results'][0]['html'])
 def test_adapter_closure_plugins_assets_and_import_mapping(self):
  files={'components.mjs':'import {tag} from "./shared.mjs"; export function components({element}) {return {Aside:({children})=>element(tag,{},children)}}','shared.mjs':'export const tag="aside"','asset.svg':'<svg/>','config.json':'{}'}
  run,response=self.invoke([{'id':'mapping','source':'import {Aside} from "custom-components"\n\n<Aside>Mapped</Aside>','path':None,'dependencies':[]}],options={'policy':'trusted','imports':{'custom-components':'components.mjs'},'dependencies':['asset.svg','config.json']},files=files);self.assertEqual(run.returncode,0,response);self.assertIn('<aside>Mapped</aside>',response['results'][0]['html']);self.assertTrue(set(files).issubset(response['results'][0]['dependencies']))
 def test_dynamic_adapter_import_refused(self):
  run,response=self.invoke(options={'policy':'trusted','components':'components.mjs'},files={'components.mjs':'export default {Aside:()=>import("./hidden.mjs")}'});self.assertNotEqual(run.returncode,0);self.assertIn('Dynamic import',response['diagnostics'][0]['message'])
 def test_plugin_dependency_and_behavior(self):
  plugin='export default function prefix(options) {return tree=>{tree.children.unshift({type:"paragraph",children:[{type:"text",value:options.text}]})}}'
  run,response=self.invoke(options={'policy':'trusted','remarkPlugins':[{'path':'plugin.mjs','options':{'text':'Plugin output'}}]},files={'plugin.mjs':plugin});self.assertEqual(run.returncode,0,response);self.assertIn('Plugin output',response['results'][0]['html']);self.assertIn('plugin.mjs',response['results'][0]['dependencies'])
 def test_nift_dependency_invalidation_site(self):
  nift=os.environ.get('NIFT','/home/nick/Repositories/nift/nift/nift')
  with tempfile.TemporaryDirectory(prefix='mdx-site-') as folder:
   path=pathlib.Path(folder);env=os.environ.copy();env.setdefault('MDX_NODE_MODULES','/usr/local/lib/node_modules')
   def write(name,content):
    file=path/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(content)
   def call(*args):
    run=subprocess.run([nift,*args],cwd=path,env=env,capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stdout+run.stderr);return run
   origin=path/'package-origin';origin.mkdir()
   for name in ['manifest.json','LICENSE']:shutil.copy2(ROOT/name,origin/name)
   shutil.copytree(ROOT/'src',origin/'src');shutil.copytree(ROOT/'renderer',origin/'renderer',ignore=shutil.ignore_patterns('node_modules','.cache'))
   subprocess.run(['git','init','-q',str(origin)],check=True)
   subprocess.run(['git','add','.'],cwd=origin,check=True)
   subprocess.run(['git','-c','user.name=mdx-test','-c','user.email=mdx@example.invalid','commit','-qm','fixture'],cwd=origin,check=True)
   call('add','file://'+str(origin),'--ref=HEAD')
   write('.nift/mdx-render.json',json.dumps({'policy':'trusted','components':'components.mjs','dependencies':['asset.txt'],'remarkPlugins':[{'path':'plugin.mjs','options':{'text':'Plugin'}}]}))
   write('components.mjs','import {tag} from "./shared.mjs";export function components({element}) {return {Aside:({children})=>element(tag,{},children)}}')
   write('shared.mjs','export const tag="aside"');write('asset.txt','first');write('plugin.mjs','export default function(options){return tree=>{tree.children.unshift({type:"paragraph",children:[{type:"text",value:options.text}]})}}')
   write('page.mdx','import Shared from "./shared.mdx"\n\n<Shared />');write('shared.mdx','<Aside>Nested first</Aside>')
   write('prepare.f','@import("mdx")\nmdx.prepare([mdx.input("page.mdx")])\n')
   write('.nift/config.json',json.dumps({'config':{'content-dir':'content/','content-ext':'.html','output-dir':'public/','output-ext':'.html','default-template':'templates/main.html','build-threads':1,'incremental-mode':'hash','pre build':'prepare.f'}}))
   write('.nift/tracked.json',json.dumps({'tracked':[{'name':'/','title':'Main','template':'templates/main.html'},{'name':'other','title':'Other','template':'templates/other.html'}]}))
   write('templates/main.html','@import("../.nift/packages/mdx/src/mdx.f")\n$[mdx.html(mdx.input("page.mdx"))]\n@content\n');write('templates/other.html','@content\n');write('content/index.html','home');write('content/other.html','other')
   call('build','--all');unrelated=(path/'public/other.html').stat().st_mtime_ns
   noop=call('build');self.assertIn('up to date',noop.stdout)
   for name,text,expected in [('shared.mdx','<Aside>Nested changed</Aside>','Nested changed'),('shared.mjs','export const tag="section"','<section>'),('asset.txt','second','<section>'),('plugin.mjs','export default function(){return tree=>{tree.children.unshift({type:"paragraph",children:[{type:"text",value:"Updated plugin"}]})}}','Updated plugin'),('.nift/mdx-render.json',json.dumps({'policy':'trusted','components':'components.mjs','dependencies':['asset.txt'],'remarkPlugins':[{'path':'plugin.mjs','options':{'text':'Different'}}]}),'<section>')]:
    write(name,text);rebuilt=call('build');self.assertIn('1 file rebuilt',rebuilt.stdout);self.assertIn(expected,(path/'public/index.html').read_text());self.assertEqual((path/'public/other.html').stat().st_mtime_ns,unrelated)
   metadata=(path/'.nift/public/index.info.json').read_text()
   for dependency in ['page.mdx','shared.mdx','components.mjs','shared.mjs','asset.txt','plugin.mjs','.nift/mdx-render.json']:self.assertEqual(metadata.count('"'+dependency+'"'),1,dependency)
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
