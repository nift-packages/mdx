#!/usr/bin/env python3
"""Isolated provisional ceiling experiment; never change production source."""
import json,os,pathlib,subprocess,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='mdx-capacity-') as folder:
 p=pathlib.Path(folder);source=(ROOT/'src/mdx.f').read_text().replace('>= 1024','>= 2048').replace('document exceeds 1024 syntax objects','document exceeds 2048 syntax objects');(p/'variant.f').write_text(source)
 (p/'exact.mdx').write_text('`x` '*1024);(p/'over.mdx').write_text('a'+'`x` '*1024)
 (p/'probe.f').write_text('@import("variant.f")\ns := mdx.with_profile("trusted")\nfor(path : ["exact.mdx","over.mdx"]){ source := open(path); t := timer(); t.start(); doc := s.parse(source); t.stop(); print({"path":path,"ok":doc.ok,"ms":t.elapsed(),"diagnostics":doc.diagnostics}.stringify()) }\n')
 cmd=[os.environ.get('NIFT','/home/nick/Repositories/nift/nift/nift'),'probe.f','--no-process'];rss=None
 if pathlib.Path('/usr/bin/time').exists():cmd=['/usr/bin/time','-f','%M','-o',str(p/'rss.txt'),*cmd]
 run=subprocess.run(cmd,cwd=p,capture_output=True,text=True,timeout=60);assert run.returncode==0,run.stderr;rows=[json.loads(x) for x in run.stdout.splitlines()];assert rows[0]['ok'] and not rows[1]['ok'];assert rows[1]['diagnostics'][0]['code']=='too_many_syntax_objects'
 if (p/'rss.txt').exists():rss=int((p/'rss.txt').read_text())
 result={'scope':'isolated 2048-object candidate, not production policy','exactObjects':2048,'overObjects':2049,'peakRssKiB':rss,'records':rows};(ROOT/'investigation/followup/capacity-probe.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
