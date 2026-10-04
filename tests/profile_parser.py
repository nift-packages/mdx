#!/usr/bin/env python3
"""Measure scanner time excluding module load, with process RSS on Linux."""
import argparse,json,os,pathlib,statistics,subprocess,tempfile,time
parser=argparse.ArgumentParser();parser.add_argument('--source',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parent.parent/'src/mdx.f');parser.add_argument('--output',type=pathlib.Path,required=True);options=parser.parse_args()
nift=os.environ.get('NIFT','/home/nick/Repositories/nift/nift/nift');rows=[]
for kind,unit in [('plain','Ordinary documentation prose with **emphasis** and links.\n'),('jsx','<A title="label">Text</A>\n'),('backticks','`a` text ' )]:
 for target in [1024,2048,4096]:
  source=unit*(target//len(unit));timings=[];walls=[];rss=[]
  with tempfile.TemporaryDirectory(prefix='mdx-profile-') as folder:
   path=pathlib.Path(folder)
   (path/'profile.f').write_text('@import('+json.dumps(str(options.source.resolve()))+')\nwatch := timer()\nwatch.start()\ndoc := mdx.parse('+json.dumps(source)+')\nwatch.stop()\nprint({"ok":doc.ok,"nodes":doc.nodes.length(),"parseMs":watch.elapsed()}.stringify())\n')
   for _ in range(3):
    command=[nift,'profile.f','--no-process'];memory=path/'memory.txt'
    if pathlib.Path('/usr/bin/time').exists():command=['/usr/bin/time','-f','%M','-o',str(memory),*command]
    start=time.perf_counter();run=subprocess.run(command,cwd=path,capture_output=True,text=True,timeout=90);assert run.returncode==0,run.stderr;result=json.loads(run.stdout);assert result['ok'],result;walls.append(time.perf_counter()-start);timings.append(result['parseMs'])
    if memory.exists():rss.append(int(memory.read_text().strip()))
  rows.append({'kind':kind,'bytes':len(source.encode()),'parse_ms_median':statistics.median(timings),'process_wall_seconds_median':statistics.median(walls),'peak_rss_kib':max(rss) if rss else None})
  print(rows[-1],flush=True)
options.output.write_text(json.dumps({'nift':nift,'source':str(options.source),'rows':rows},indent=2)+'\n')
