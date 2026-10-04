import os
import json, subprocess, time, statistics, pathlib
P=pathlib.Path(__file__).resolve().parent
NIFT=os.environ.get('NIFT', '/home/nick/Repositories/nift/nift/nift')
cases={'small':'# Small\n\nHello **world**.\n','realistic':'# Documentation\n\n'+('\n## Install\n\nFollow [instructions](https://example.org).\n\n- Configure credentials\n- Run your application\n\n```js\nconsole.log("ready")\n```\n'*12),'components':'# Components\n\n'+('<Aside type="warning">Important **content**.</Aside>\n\n'*45)}
results={'environment':{'node':subprocess.check_output(['node','--version'],text=True).strip(),'nift':NIFT},'cases':{}}
def invoke(cmd):
 t=time.perf_counter(); p=subprocess.run(cmd,cwd=P,capture_output=True,text=True,check=True); return time.perf_counter()-t,p.stdout
for name,source in cases.items():
 doc={'ok':True,'source':source,'path':None,'dependencies':[]}
 (P/'parse-bench.f').write_text('@import("mdx-prototype.f")\nprint(mdx.parse('+json.dumps(source)+').ok)\n')
 parse=[]; spawned=[]; timers=[]
 for _ in range(3):
  t,o=invoke([NIFT,'parse-bench.f','--no-process']); assert o.strip()=='true'; parse.append(t)
  t,o=invoke(['node','helper.mjs',json.dumps(doc)]); spawned.append(t); timers.append(json.loads(o))
 row={'bytes':len(source.encode()),'parser_process_wall_seconds_median':statistics.median(parse),'renderer_process_wall_seconds_median':statistics.median(spawned),'renderer_metrics':timers}
 for count in [100,1000]:
  (P/'batch-request.json').write_text(json.dumps([doc]*count))
  t,o=invoke(['node','helper.mjs','--file','batch-request.json']); records=json.loads(o)
  row[f'batch_{count}']={'wall_seconds':t,'compile_ms_sum':sum(r['timing']['compileMs'] for r in records),'render_ms_sum':sum(r['timing']['renderMs'] for r in records),'peak_rss_kib':max(r['maxRssKiB'] for r in records)}
 start=time.perf_counter()
 for _ in range(100): invoke(['node','helper.mjs',json.dumps(doc)])
 row['spawn_100_wall_seconds']=time.perf_counter()-start
 results['cases'][name]=row
 (P/'benchmark-results.json').write_text(json.dumps(results,indent=2)+'\n')
 print(name,row['spawn_100_wall_seconds'],row['batch_100']['wall_seconds'],flush=True)
results['empty_node_startup_seconds_median']=statistics.median(invoke(['node','-e',''])[0] for _ in range(5))
(P/'benchmark-results.json').write_text(json.dumps(results,indent=2)+'\n')
