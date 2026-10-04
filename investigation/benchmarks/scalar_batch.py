#!/usr/bin/env python3
"""Compare identical pure Nift parse + render workloads, not site build totals."""
import json,os,pathlib,subprocess,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
nift=os.environ.get('NIFT','/home/nick/Repositories/nift/nift/nift')
sources=[f'# Page {i}\n\n'+('Documentation with **emphasis**, installation and configuration. '*10)+'\n\n| Key | Value |\n| --- | --- |\n| a | b |\n\n<Aside>Expression {1+2}.</Aside>\n' for i in range(100)]
records=[];htmls=[]
with tempfile.TemporaryDirectory(prefix='mdx-scalar-batch-') as folder:
 path=pathlib.Path(folder);(path/'.nift').mkdir();(path/'.nift/mdx-render.json').write_text(json.dumps({'policy':'trusted','components':'components.mjs'}));(path/'components.mjs').write_text('export function components({element}){return {Aside:({children})=>element("aside",{},children)}}')
 for mode in ['scalar','batch']:
  script='@import('+json.dumps(str(ROOT/'src/mdx.f'))+')\nsources := '+json.dumps(sources)+'\noutputs := []\n'
  if mode=='scalar':script+='for(source : sources){ outputs.push(mdx.html(mdx.parse(source))) }\n'
  else:script+='documents := []\nfor(source : sources){ documents.push(mdx.parse(source)) }\nresult := mdx.prepare(documents)\nfor(item : result.results){ outputs.push(item.html) }\n'
  script+='output := file("outputs.json"); output.open("w"); output.write_val(outputs); output.save(); output.close()\n';(path/'run.f').write_text(script)
  env=os.environ.copy();env.setdefault('MDX_NODE_MODULES','/usr/local/lib/node_modules');started=time.perf_counter();run=subprocess.run(['/usr/bin/time','-f','%M','-o',str(path/'rss.txt'),nift,'run.f'],cwd=path,env=env,capture_output=True,text=True,timeout=300);assert run.returncode==0,run.stdout+run.stderr
  records.append({'mode':mode,'documents':100,'parseAndRenderSeconds':time.perf_counter()-started,'maximumResidentKiB':int((path/'rss.txt').read_text()),'helperInvocations':100 if mode=='scalar' else 1});htmls.append(json.loads((path/'outputs.json').read_text()))
 assert htmls[0]==htmls[1]
(ROOT/'investigation/checkpoints/CP21-scalar-batch.json').write_text(json.dumps({'outputsIdentical':True,'records':records},indent=2)+'\n');print(json.dumps(records))
