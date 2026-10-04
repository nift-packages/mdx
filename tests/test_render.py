#!/usr/bin/env python3
import json,os,pathlib,subprocess,tempfile,unittest,shutil
ROOT=pathlib.Path(__file__).resolve().parent.parent
class RendererTests(unittest.TestCase):
 def invoke(self,documents=None,options=None,raw=None,files=None):
  with tempfile.TemporaryDirectory(prefix='mdx protocol café ') as folder:
   path=pathlib.Path(folder);request={'version':1,'documents':documents or [{'id':'one','source':'# Hello','path':None,'dependencies':[]}],'options':options or {'policy':'trusted'}}
   for name,content in (files or {}).items():
    file=path/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(content,encoding="utf-8",newline="")
   (path/'request.json').write_text(raw if raw is not None else json.dumps(request),encoding="utf-8",newline="")
   env=os.environ.copy();env.setdefault('MDX_NODE_MODULES','/usr/local/lib/node_modules')
   run=subprocess.run(['node',str(ROOT/'renderer/cli.mjs'),'--request','request.json','--response','response.json'],cwd=path,env=env,capture_output=True,text=True,timeout=20)
   return run,json.loads((path/'response.json').read_text(encoding="utf-8"))
 def test_source_aware_diagnostics(self):
  source='---\ntitle: Example\n---\n\nimport Missing from "unmapped"\n\n<Missing />'
  run,response=self.invoke([{'id':'imports','source':source,'path':'article.mdx','dependencies':[]}])
  error=response['results'][0]['diagnostics'][0];self.assertEqual(error['path'],'article.mdx');self.assertEqual(error['line'],5);self.assertEqual(error['column'],1)
  run,response=self.invoke([{'id':'unknown','source':'<Unknown />','path':'article.mdx','dependencies':[]}])
  error=response['results'][0]['diagnostics'][0];self.assertEqual(error['component'],'Unknown')
  run,response=self.invoke([{'id':'adapter','source':'<Aside />','path':'article.mdx','dependencies':[]}],options={'policy':'trusted','components':'components.mjs'},files={'components.mjs':'export default {Aside:()=>{throw new Error("broken adapter")}}'})
  error=response['results'][0]['diagnostics'][0];self.assertEqual(error['stage'],'render');self.assertEqual(error['path'],'article.mdx');self.assertEqual(error['component'],'Aside');self.assertEqual(error['adapterPath'],'components.mjs');self.assertIsNone(error['line'])
 def test_runtime_source_maps(self):
  source='---\ntitle: Example\n---\n\n# Runtime\n\n{(() => { throw new Error("expression failed") })()}'
  run,response=self.invoke([{'id':'runtime','source':source,'path':'article.mdx','dependencies':[]}]);error=response['results'][0]['diagnostics'][0]
  self.assertEqual(error['stage'],'render');self.assertEqual(error['path'],'article.mdx');self.assertEqual(error['line'],7);self.assertIsInstance(error['column'],int)
  run,response=self.invoke([{'id':'child','source':'import Child from "./child.mdx"\n\n<Child />','path':'root.mdx','dependencies':[{'path':'child.mdx'}]}],files={'child.mdx':source});error=response['results'][0]['diagnostics'][0]
  self.assertEqual(error['path'],str(error['path']));self.assertTrue(error['path'].endswith('child.mdx'));self.assertEqual(error['line'],7)
 def test_thousand_document_batch(self):
  sources=['# Heading\n\nA paragraph.','| A | B |\n| - | - |\n| 1 | 2 |','<div>Static</div>','{1 + 2}','- One\n- Two']
  documents=[{'id':str(i),'source':sources[i%len(sources)],'path':None,'dependencies':[]} for i in range(1000)]
  run,response=self.invoke(documents);self.assertEqual(run.returncode,0,response);self.assertEqual([r['id'] for r in response['results']],[str(i) for i in range(1000)])
  for i,source in enumerate(sources):
   scalar,single=self.invoke([documents[i]]);self.assertEqual(scalar.returncode,0);self.assertEqual(response['results'][i]['html'],single['results'][0]['html'])
  documents[500]['source']='<Unknown />';run,mixed=self.invoke(documents);self.assertNotEqual(run.returncode,0);self.assertEqual([r['id'] for r in mixed['results'] if not r['ok']],['500']);self.assertEqual(mixed['results'][501]['html'],response['results'][501]['html'])
 def test_content_cache(self):
  with tempfile.TemporaryDirectory(prefix='mdx-cache-') as folder:
   path=pathlib.Path(folder);env=os.environ.copy();env.setdefault('MDX_NODE_MODULES','/usr/local/lib/node_modules')
   runtime_source=ROOT/'renderer/node_modules'
   if not runtime_source.exists():runtime_source=pathlib.Path('/tmp/mdx-runtime-cp02/node_modules')
   if runtime_source.exists():
    shutil.copytree(runtime_source,path/'runtime/node_modules');env['MDX_NODE_MODULES']=str(path/'runtime/node_modules')
   helper=path/'renderer';shutil.copytree(ROOT/'renderer',helper,ignore=shutil.ignore_patterns('node_modules','.cache'))
   options={'policy':'trusted','cache':'content','components':'components.mjs','dependencies':['asset.txt'],'remarkPlugins':[{'path':'plugin.mjs'}]}
   document={'id':'cache','source':'import Child from "./child.mdx"\n\n<Aside><Child /></Aside>','path':'page.mdx','dependencies':[{'path':'child.mdx'}]}
   files={'child.mdx':'# Child','components.mjs':'import {tag} from "./shared.mjs";export function components({element}){return {Aside:({children})=>element(tag,{},children)}}','shared.mjs':'export const tag="aside"','asset.txt':'first','plugin.mjs':'export default function(){return tree=>{}}'}
   for name,content in files.items():(path/name).write_text(content,encoding="utf-8",newline="")
   def invoke(raw=False):
    (path/'request.json').write_text(json.dumps({'version':1,'documents':[document],'options':options}),encoding="utf-8",newline="")
    run=subprocess.run(['node',str(helper/'cli.mjs'),'--request','request.json','--response','response.json'],cwd=path,env=env,capture_output=True,text=True,timeout=30)
    response=json.loads((path/'response.json').read_text(encoding="utf-8"))
    if raw:return run,response
    self.assertEqual(run.returncode,0,response);return response['results'][0]
   cold=invoke();warm=invoke();self.assertFalse(cold['cacheHit']);self.assertTrue(warm['cacheHit']);self.assertEqual(cold['html'],warm['html']);self.assertEqual(cold['dependencies'],warm['dependencies'])
   for name in files:
    (path/name).write_text(files[name]+'\n',encoding="utf-8",newline="");self.assertFalse(invoke()['cacheHit'],name);self.assertTrue(invoke()['cacheHit'],name)
   (helper/'cache.mjs').write_text((helper/'cache.mjs').read_text(encoding="utf-8")+'\n',encoding="utf-8",newline="");self.assertFalse(invoke()['cacheHit']);self.assertTrue(invoke()['cacheHit'])
   lock=helper/'package-lock.json';lock.write_text(lock.read_text(encoding="utf-8")+'\n',encoding="utf-8",newline="");self.assertFalse(invoke()['cacheHit']);self.assertTrue(invoke()['cacheHit'])
   if (path/'runtime/node_modules/unified/lib/index.js').exists():
    transitive=path/'runtime/node_modules/unified/lib/index.js';transitive.write_text(transitive.read_text(encoding='utf-8')+'\n',encoding='utf-8',newline='');self.assertFalse(invoke()['cacheHit']);self.assertTrue(invoke()['cacheHit'])
   options['remarkPlugins'][0]['options']={'changed':True};self.assertFalse(invoke()['cacheHit']);self.assertTrue(invoke()['cacheHit'])
   env['MDX_CACHE_TEST_CONTEXT']='changed';self.assertFalse(invoke()['cacheHit']);self.assertTrue(invoke()['cacheHit'])
   document['source']+='\n';self.assertFalse(invoke()['cacheHit']);self.assertTrue(invoke()['cacheHit'])
   for file in (path/'.nift/mdx-cache').glob('*.json'):file.write_text('corrupt',encoding="utf-8",newline="")
   self.assertFalse(invoke()['cacheHit']);self.assertTrue(invoke()['cacheHit'])
   options['cache']=False;disabled=invoke();self.assertFalse(disabled['cacheHit']);self.assertEqual(disabled['html'],cold['html']);options['cache']='content'
   for file in (path/'.nift/mdx-cache').glob('*.json'):file.unlink()
   (path/'request.json').write_text(json.dumps({'version':1,'documents':[document],'options':options}),encoding="utf-8",newline="")
   workers=[subprocess.Popen(['node',str(helper/'cli.mjs'),'--request','request.json','--response',f'concurrent-{i}.json'],cwd=path,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for i in range(2)]
   for index,worker in enumerate(workers):
    output,error=worker.communicate(timeout=30);self.assertEqual(worker.returncode,0,error+(path/f"concurrent-{index}.json").read_text(encoding="utf-8"))
   self.assertEqual(json.loads((path/'concurrent-0.json').read_text(encoding="utf-8"))['results'][0]['html'],json.loads((path/'concurrent-1.json').read_text(encoding="utf-8"))['results'][0]['html']);self.assertTrue(invoke()['cacheHit'])
   options['policy']='untrusted';run,response=invoke(True);self.assertNotEqual(run.returncode,0);options['policy']='trusted'
   (path/'asset.txt').unlink();run,response=invoke(True);self.assertNotEqual(run.returncode,0)
 @unittest.skipUnless(os.name=='nt','Windows native path contract')
 def test_windows_native_input_paths(self):
  nift=os.environ['NIFT']
  with tempfile.TemporaryDirectory(prefix='mdx native café ') as folder:
   path=pathlib.Path(folder);(path/'nested').mkdir();(path/'nested/root.mdx').write_text('import Child from "./child.mdx"\n\n<Child />',encoding='utf-8',newline='');(path/'nested/child.mdx').write_text('# Child',encoding='utf-8',newline='')
   sources=[str(path/'nested/root.mdx'),'nested\\root.mdx','C:page.mdx','\\\\server\\share\\page.mdx']
   script='@import('+json.dumps(str(ROOT/'src/mdx.f'))+')\n'+''.join('print(mdx.input('+json.dumps(source)+').stringify())\n' for source in sources)
   (path/'paths.f').write_text(script,encoding='utf-8',newline='');run=subprocess.run([nift,'paths.f','--no-process'],cwd=path,capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stderr)
   records=[json.loads(x) for x in run.stdout.splitlines()];self.assertTrue(records[0]['ok']);self.assertTrue(records[1]['ok']);self.assertEqual(records[0]['path'],'nested/root.mdx');self.assertEqual(records[1]['dependencies'][0]['path'],'nested/child.mdx')
   for record in records[2:]:self.assertEqual(record['diagnostics'][0]['code'],'path_escape')
 def test_documented_example(self):
  nift=os.environ.get('NIFT','/home/nick/Repositories/nift/nift/nift')
  with tempfile.TemporaryDirectory(prefix='mdx-doc-example-') as folder:
   path=pathlib.Path(folder)/'site';shutil.copytree(ROOT/'examples/basic',path);origin=path.parent/'origin';origin.mkdir();env=os.environ.copy();env.setdefault('MDX_NODE_MODULES','/usr/local/lib/node_modules')
   for name in ['manifest.json','LICENSE']:shutil.copy2(ROOT/name,origin/name)
   shutil.copytree(ROOT/'src',origin/'src');shutil.copytree(ROOT/'renderer',origin/'renderer',ignore=shutil.ignore_patterns('node_modules','.cache'))
   subprocess.run(['git','init','-q',str(origin)],check=True);subprocess.run(['git','add','.'],cwd=origin,check=True);subprocess.run(['git','-c','user.name=example','-c','user.email=example@example.invalid','commit','-qm','example package'],cwd=origin,check=True)
   def call(*args):
    run=subprocess.run([nift,*args],cwd=path,env=env,capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stdout+run.stderr);return run
   call('add',origin.as_uri(),'--ref=HEAD');call('build','--all');html=(path/'public/index.html').read_text(encoding='utf-8')
   for expected in ['<aside>','A static component','expression result is 3','Imported document','<table>']:self.assertIn(expected,html)
   self.assertNotIn('<script',html);self.assertNotIn('react-dom',html);mtime=(path/'public/index.html').stat().st_mtime_ns;self.assertIn('up to date',call('build').stdout);self.assertEqual(mtime,(path/'public/index.html').stat().st_mtime_ns)
   metadata=(path/'.nift/public/index.info.json').read_text(encoding='utf-8')
   for dependency in ['page.mdx','shared.mdx','components.mjs','.nift/mdx-render.json']:self.assertEqual(metadata.count('"'+dependency+'"'),1,dependency)
 def test_async_component_factory_refused(self):
  run,response=self.invoke(options={'policy':'trusted','components':'components.mjs'},files={'components.mjs':'export async function components(){return {Aside:()=>"async"}}'})
  self.assertNotEqual(run.returncode,0);self.assertIn('Async component factories',response['diagnostics'][0]['message'])
 def test_mapped_default_named_namespace_asset_exports(self):
  source='import Logo, {label} from "@assets/logo.svg"\nimport * as Assets from "@assets/logo.svg"\n\n<img src={Logo.src} width={Logo.width} />\n\n{label} {Assets.default.src}'
  run,response=self.invoke([{'id':'asset','source':source,'path':None,'dependencies':[]}],options={'policy':'trusted','imports':{'@assets/logo.svg':'asset.mjs'},'dependencies':['logo.svg']},files={'asset.mjs':'export const label="Asset";export default {src:"/logo.svg",width:12}','logo.svg':'<svg/>'})
  self.assertEqual(run.returncode,0,response);html=response['results'][0]['html'];self.assertIn('src="/logo.svg"',html);self.assertIn('width="12"',html);self.assertIn('Asset',html);self.assertTrue({'asset.mjs','logo.svg'}.issubset(response['results'][0]['dependencies']))
 def test_installed_nift_facade(self):
  nift=os.environ.get('NIFT','/home/nick/Repositories/nift/nift/nift')
  with tempfile.TemporaryDirectory(prefix='mdx-installed-') as folder:
   path=pathlib.Path(folder);env=os.environ.copy();env.setdefault('MDX_NODE_MODULES','/usr/local/lib/node_modules')
   subprocess.run([nift,'add',*( [ROOT.as_uri(),'--ref=HEAD'] if os.name=='nt' else [str(ROOT)] )],cwd=path,env=env,capture_output=True,text=True,check=True)
   (path/'.nift/mdx-render.json').write_text(json.dumps({'policy':'trusted'}),encoding="utf-8",newline="")
   (path/'page.mdx').write_text('# Prepared\n\nHello.',encoding="utf-8",newline="")
   (path/'render.f').write_text('@import("mdx")\nmdx.prepare([mdx.input("page.mdx")])\nprint(mdx.html(mdx.input("page.mdx")))\nprint(mdx.html(mdx.parse("# Inline")))\n',encoding="utf-8",newline="")
   run=subprocess.run([nift,'render.f'],cwd=path,env=env,capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stderr);self.assertIn('mdx-prepared',run.stdout);self.assertIn('mdx-inline',run.stdout)
   blocked=subprocess.run([nift,'render.f','--no-process'],cwd=path,env=env,capture_output=True,text=True);self.assertNotEqual(blocked.returncode,0);self.assertIn('execution disabled',blocked.stderr)
   (path/'page.mdx').write_text('# Changed',encoding="utf-8",newline="")
   (path/'stale.f').write_text('@import("mdx")\nprint(mdx.html(mdx.input("page.mdx")))\n',encoding="utf-8",newline="")
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
    file=path/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(content,encoding="utf-8",newline="")
   def call(*args):
    run=subprocess.run([nift,*args],cwd=path,env=env,capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stdout+run.stderr);return run
   origin=path/'package-origin';origin.mkdir()
   for name in ['manifest.json','LICENSE']:shutil.copy2(ROOT/name,origin/name)
   shutil.copytree(ROOT/'src',origin/'src');shutil.copytree(ROOT/'renderer',origin/'renderer',ignore=shutil.ignore_patterns('node_modules','.cache'))
   subprocess.run(['git','init','-q',str(origin)],check=True)
   subprocess.run(['git','add','.'],cwd=origin,check=True)
   subprocess.run(['git','-c','user.name=mdx-test','-c','user.email=mdx@example.invalid','commit','-qm','fixture'],cwd=origin,check=True)
   call('add',origin.as_uri(),'--ref=HEAD')
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
    write(name,text);rebuilt=call('build');self.assertIn('1 file rebuilt',rebuilt.stdout);self.assertIn(expected,(path/'public/index.html').read_text(encoding="utf-8"));self.assertEqual((path/'public/other.html').stat().st_mtime_ns,unrelated)
   metadata=(path/'.nift/public/index.info.json').read_text(encoding="utf-8")
   for dependency in ['page.mdx','shared.mdx','components.mjs','shared.mjs','asset.txt','plugin.mjs','.nift/mdx-render.json']:self.assertEqual(metadata.count('"'+dependency+'"'),1,dependency)
 def test_gfm_heading_ids_and_markdown_defaults(self):
  source='# Duplicate\n\n# Duplicate\n\n~~gone~~ and https://example.org\n\n| Name | Value |\n| --- | --- |\n| One | Two |\n\n- [x] Done\n- [ ] Todo\n\nReference[^note].\n\n[^note]: Footnote text.\n\n"Straight quotes" -- plain.\n'
  run,response=self.invoke([{'id':'gfm','source':source,'path':None,'dependencies':[]}]);self.assertEqual(run.returncode,0,response);html=response['results'][0]['html']
  for fragment in ['id="mdx-duplicate"','id="mdx-duplicate-1"','<del>gone</del>','href="https://example.org"','<table>','type="checkbox"','Footnote text','data-footnote']:self.assertIn(fragment,html)
  self.assertNotIn('“',html);self.assertNotIn('”',html);self.assertIn('-- plain',html)
 def test_jsx_html_and_inert_code(self):
  source='<div><em>HTML</em></div>\n\n```mdx\nimport Hidden from "./hidden.mdx"\n<Unknown />\n{process.exit()}\n```'
  run,response=self.invoke([{'id':'code','source':source,'path':None,'dependencies':[]}]);self.assertEqual(run.returncode,0,response);self.assertIn('<div><em>HTML</em></div>',response['results'][0]['html']);self.assertIn('process.exit',response['results'][0]['html'])
  run,response=self.invoke([{'id':'comment','source':'<!-- HTML comment -->','path':None,'dependencies':[]}]);self.assertNotEqual(run.returncode,0)
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
