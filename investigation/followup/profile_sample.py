#!/usr/bin/env python3
import json,os,pathlib,subprocess,tempfile,sys
ROOT=pathlib.Path(__file__).resolve().parents[2];upstream=pathlib.Path('/tmp/capgo-upstream-planning');NIFT=os.environ.get('NIFT','/home/nick/Repositories/nift/nift/nift')
rows=json.loads((ROOT/'investigation/checkpoints/CP13-capgo-corpus.json').read_text())['records'];paths=[r['path'] for r in sorted(rows,key=lambda x:x['milliseconds'],reverse=True)[:20]]
variants=[pathlib.Path(x).resolve() for x in sys.argv[1:]] if len(sys.argv)>1 else [ROOT/'src/mdx.f',pathlib.Path('/tmp/mdx-byte-view.f'),pathlib.Path('/tmp/mdx-instrumented.f')];results=[]
phases=['line_info','backtick_matches','frontmatter','fence','scan_js','jsx','point','node','attribute','plain_end','jsx_name','import_specifier']
with tempfile.TemporaryDirectory(prefix='mdx-profile-sample-') as folder:
 p=pathlib.Path(folder)
 for variant in variants:
  script='@import('+json.dumps(str(variant))+')\nfor(path : '+json.dumps(paths)+'){ scanner := mdx.with_profile("trusted"); source := open('+json.dumps(str(upstream)+'/' )+'+path); watch := timer(); watch.start(); doc := scanner.parse(source); watch.stop(); print({"path":path,"ms":watch.elapsed(),"ok":doc.ok'
  if 'instrumented' in str(variant):script+=',"phases":{'+','.join(json.dumps(n)+':{"ms":scanner.phase_'+n+',"calls":scanner.calls_'+n+'}' for n in phases)+'}'
  script+='}.stringify()) }\n';(p/'sample.f').write_text(script);run=subprocess.run([NIFT,'sample.f','--no-process'],cwd=p,capture_output=True,text=True,timeout=300);assert run.returncode==0,run.stderr;results.append({'variant':variant.name,'records':[json.loads(x) for x in run.stdout.splitlines()]});(ROOT/'investigation/followup'/('sample-'+variants[-1].stem+'.json')).write_text(json.dumps(results,indent=2)+'\n');print(variant.name,sum(r['ms'] for r in results[-1]['records']),flush=True)
(ROOT/'investigation/followup'/('sample-'+variants[-1].stem+'.json')).write_text(json.dumps(results,indent=2)+'\n')
