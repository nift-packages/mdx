#!/usr/bin/env python3
"""Installed Nift build benchmark; Linux invocation/RSS instrumentation."""
import json,os,pathlib,shutil,subprocess,sys,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
NIFT=os.environ.get('NIFT','/home/nick/Repositories/nift/nift/nift')
NODE=shutil.which('node')
stage=os.environ.get('MDX_BENCH_STAGE','CP15')
counts=[int(n) for n in sys.argv[1:]] or [100,500,1000]
records=[]
with tempfile.TemporaryDirectory(prefix='mdx batch café ') as folder:
 base=pathlib.Path(folder);origin=base/'origin';origin.mkdir()
 for name in ['manifest.json','LICENSE']:shutil.copy2(ROOT/name,origin/name)
 shutil.copytree(ROOT/'src',origin/'src');shutil.copytree(ROOT/'renderer',origin/'renderer',ignore=shutil.ignore_patterns('node_modules','.cache'))
 subprocess.run(['git','init','-q',str(origin)],check=True);subprocess.run(['git','add','.'],cwd=origin,check=True);subprocess.run(['git','-c','user.name=benchmark','-c','user.email=benchmark@example.invalid','commit','-qm','fixture'],cwd=origin,check=True)
 for count in counts:
  project=base/str(count);project.mkdir();env=os.environ.copy();env.setdefault('MDX_NODE_MODULES','/usr/local/lib/node_modules')
  def write(name,content):
   p=project/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
  def call(args,timeout=600):
   result=subprocess.run([NIFT,*args],cwd=project,env=env,capture_output=True,text=True,timeout=timeout);assert result.returncode==0,result.stdout+result.stderr;return result
  call(['add','file://'+str(origin),'--ref=HEAD'])
  binpath=project/'bin';binpath.mkdir();log=project/'launches.jsonl'
  wrapper=binpath/'node';wrapper.write_text('#!'+sys.executable+'\nimport os,sys,json\nwith open('+repr(str(log))+',"a") as f: f.write(json.dumps(sys.argv[1:])+"\\n")\nos.execv('+repr(NODE)+',['+repr(NODE)+',*sys.argv[1:]])\n');wrapper.chmod(0o755);env['PATH']=str(binpath)+os.pathsep+env['PATH']
  write('.nift/mdx-render.json',json.dumps({'policy':'trusted','timeoutMs':600000,'components':'components.mjs',**({'cache':'content'} if os.environ.get('MDX_BENCH_CACHE') else {})}))
  write('components.mjs','export function components({element}){return {Aside:({children})=>element("aside",{},children)}}')
  write('shared.mdx','## Shared\n\nReusable text.')
  paths=[];tracked=[]
  for i in range(count):
   name=f'page-{i}';path=f'pages/{name}.mdx';paths.append(path);tracked.append({'name':name,'title':name,'template':'templates/main.html'})
   prose=('A documentation paragraph explains installation, configuration and runtime behavior. '*8)
   source=(f'---\ntitle: Page {i}\n---\n\n# Page {i}\n\n'+prose+'\n\n| Key | Value |\n| --- | --- |\n| one | two |\n\n- First\n- Second\n\n```js\nconst value = 1;\n```\n\n')
   if i%5==0:source='import Shared from "../shared.mdx"\n\n'+source.split('---\n',2)[-1]+'<Shared />\n'
   elif i%5==1:source+='<Aside>Component text with **emphasis**.</Aside>\n'
   write(path,source)
   write(f'content/{name}.html','@import("../.nift/packages/mdx/src/mdx.f")\n$[mdx.html(mdx.input('+json.dumps(path)+'))]\n')
  write('templates/main.html','<!doctype html>\n<html><body>@content</body></html>\n')
  write('.nift/config.json',json.dumps({'config':{'content-dir':'content/','content-ext':'.html','output-dir':'public/','output-ext':'.html','default-template':'templates/main.html','build-threads':1,'incremental-mode':'hash','pre build':'prepare.f'}}))
  write('.nift/tracked.json',json.dumps({'tracked':tracked}))
  write('prepare.f','@import("mdx")\nwatch := timer(); watch.start(); documents := []\nfor(path : '+json.dumps(paths)+'){ documents.push(mdx.input(path)) }\nwatch.stop(); parser_ms := watch.elapsed(); watch.start(); response := mdx.prepare(documents); watch.stop()\nmetrics := file(".nift/metrics.json"); metrics.open("w"); metrics.write_val({"parserMs":parser_ms,"prepareMs":watch.elapsed(),"results":response.results}); metrics.save(); metrics.close()\n')
  builds=[]
  for mode in (['cold','warm','cached-warm'] if os.environ.get('MDX_BENCH_CACHE') else ['cold','warm']):
   log.write_text('');started=time.perf_counter();result=call(['build','--all'] if mode=='cold' else ['build']);wall=time.perf_counter()-started
   metrics=json.loads((project/'.nift/metrics.json').read_text());launches=[json.loads(x) for x in log.read_text().splitlines()]
   assert sum('--request' in x for x in launches)==1,launches
   outputs=list((project/'public').glob('*.html'));assert len(outputs)==count
   assert all('<html>' in x.read_text() and '<h1' in x.read_text() and 'react-dom' not in x.read_text() for x in outputs)
   if mode!='cold':assert 'up to date' in result.stdout,result.stdout
   timings={k:sum(r['timing'][k] for r in metrics['results']) for k in ['compileMs','evaluateMs','renderMs','totalMs']}
   builds.append({'mode':mode,'fullBuildSeconds':wall,'parserMs':metrics['parserMs'],'prepareMs':metrics['prepareMs'],'helperTotalsMs':timings,'nodeLaunches':len(launches),'helperInvocations':1,'outputs':len(outputs),'cacheHits':sum(r.get('cacheHit',False) for r in metrics['results'])})
  records.append({'pages':count,'builds':builds});print(json.dumps(records[-1]),flush=True)
  (ROOT/f'investigation/checkpoints/{stage}-site-results.json').write_text(json.dumps(records,indent=2)+'\n')
