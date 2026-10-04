#!/usr/bin/env python3
import json,os,pathlib,subprocess,tempfile,time,shutil,sys
ROOT=pathlib.Path(__file__).resolve().parent.parent;NIFT=os.environ.get('NIFT',shutil.which('nift') or '/home/nick/Repositories/nift/nift/nift')
with tempfile.TemporaryDirectory(prefix='mdx-profiles-') as folder:
 p=pathlib.Path(folder)
 (p/'exact.mdx').write_text('x'*65536);(p/'over.mdx').write_text('x'*65537);(p/'lines.mdx').write_text('\n'*8193)
 (p/'exact-lines.mdx').write_text('\n'*8192)
 (p/'unicode.mdx').write_text('é'*32768)
 for index in range(33):(p/f'large-{index}.mdx').write_text('x'*65536)
 (p/'graph.mdx').write_text(''.join(f'import "./large-{index}.mdx"\n' for index in range(33)))
 imports=''.join(f'import "./large-{index}.mdx"\n' for index in range(32))
 (p/'exact-graph.mdx').write_text(imports)
 (p/'large-31.mdx').write_text('x'*(65536-len(imports.encode())))
 script='@import('+json.dumps(str(ROOT/'src/mdx.f'))+')\ntrusted := mdx.with_profile("trusted")\n'
 script+='''print(mdx.parse(open("exact.mdx")).diagnostics[0].code)
for(path : ["exact.mdx","over.mdx","lines.mdx","unicode.mdx","exact-lines.mdx"]) {
 watch := timer(); watch.start(); doc := trusted.input(path); watch.stop()
 print({"path":path,"ok":doc.ok,"diagnostics":doc.diagnostics,"milliseconds":watch.elapsed()}.stringify())
}
print(trusted.input("graph.mdx").diagnostics[0].code)
print(trusted.input("exact-graph.mdx").ok)
print(mdx.profile_name)
'''
 (p/'test.f').write_text(script)
 command=[NIFT,'test.f','--no-process']
 if sys.platform=='linux' and pathlib.Path('/usr/bin/time').exists(): command=['/usr/bin/time','-f','%M','-o',str(p/'memory.txt'),*command]
 started=time.perf_counter();run=subprocess.run(command,cwd=p,capture_output=True,text=True,timeout=180);assert run.returncode==0,run.stderr
 lines=run.stdout.splitlines();assert lines[0]=='source_too_large';records=[json.loads(line) for line in lines[1:6]]
 assert [record['ok'] for record in records]==[True,False,False,True,True],records
 assert records[1]['diagnostics'][0]['code']=='source_too_large';assert records[2]['diagnostics'][0]['code']=='too_many_lines'
 assert lines[6]=='aggregate_source_limit';assert lines[7]=='true';assert lines[8]=='bounded'
 evidence={'records':records,'full_wall_seconds':time.perf_counter()-started,'peak_rss_kib':int((p/'memory.txt').read_text()) if (p/'memory.txt').exists() else None}
 (ROOT/'investigation/checkpoints/CP13-profile-results.json').write_text(json.dumps(evidence,indent=2)+'\n')
 print('PASS bounded defaults, independent trusted facade, exact/over64KiB,8192-line limit, UTF-8 bytes,2MiB graph bound')
 print(json.dumps(evidence))
