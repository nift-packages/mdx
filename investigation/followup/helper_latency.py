#!/usr/bin/env python3
"""Existing renderer latency on real ordinary/large fixtures, without preservation parsing."""
import json,os,pathlib,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[2];upstream=pathlib.Path('/tmp/capgo-upstream-planning');prefix='apps/docs/src/content/docs/docs/'
paths=[prefix+'plugins/intent-launcher/index.mdx',prefix+'plugins/inappbrowser/getting-started.mdx'];records=[];env=os.environ.copy();env.setdefault('MDX_NODE_MODULES','/usr/local/lib/node_modules')
for index,path in enumerate(paths):
 source=(upstream/path).read_text();request=upstream/f'.mdx-latency-{index}.json';response=upstream/f'.mdx-latency-result-{index}.json'
 try:
  request.write_text(json.dumps({'version':1,'documents':[{'id':path,'path':path,'source':source,'dependencies':[]}],'options':{'policy':'trusted'}}));started=time.perf_counter();run=subprocess.run(['node',str(ROOT/'renderer/cli.mjs'),'--request',request.name,'--response',response.name],cwd=upstream,env=env,capture_output=True,text=True,timeout=30);result=json.loads(response.read_text());assert run.returncode==0,result;row=result['results'][0];records.append({'path':path,'processWallMilliseconds':1000*(time.perf_counter()-started),'timing':row['timing'],'htmlBytes':len(row['html'].encode()),'ok':row['ok']})
 finally:request.unlink(missing_ok=True);response.unlink(missing_ok=True)
(ROOT/'investigation/followup/helper-latency.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(records))
