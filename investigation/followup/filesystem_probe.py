#!/usr/bin/env python3
"""Read-only filesystem spelling/API probes, including fatal operations in isolation."""
import json,os,pathlib,platform,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2];NIFT=os.environ.get('NIFT','/home/nick/Repositories/nift/nift/nift')
records=[];operations=[]
with tempfile.TemporaryDirectory(prefix='mdx type spaces ') as folder:
 p=pathlib.Path(folder);(p/'normal.mdx').write_text('text');(p/'directory').mkdir();(p/'nested').mkdir();(p/'nested/file.mdx').write_text('nested');(p/'nested/directory').mkdir();(p/'space file.mdx').write_text('spaces');(p/'space directory').mkdir();(p/'café.mdx').write_text('unicode');(p/'café directory').mkdir()
 (p/'.hidden directory').mkdir();(p/'.hidden file.mdx').write_text('hidden')
 try:(p/'directory link').symlink_to(p/'directory',target_is_directory=True)
 except OSError:pass
 inputs=['normal.mdx','directory','nested/file.mdx','nested/directory','space file.mdx','space directory','café.mdx','café directory',str(p/'normal.mdx'),str(p/'nested/directory')]
 if os.name=='nt':
  inputs+=['nested\\file.mdx','nested\\directory',str(p/'café.mdx')]
  inputs += ['\\\\?\\'+str(p/name) for name in ['normal.mdx','directory','space file.mdx','space directory','café.mdx','café directory']]
 suffixes=['','/.','\\.','/','\\','/./','\\.\\']
 candidates=[path+suffix for path in inputs for suffix in suffixes]
 script='for(candidate : '+json.dumps(candidates,ensure_ascii=False)+'){ handle := file(candidate); try { print({"path":candidate,"normalized":handle.path(),"exists":exists(candidate),"isFile":is_file(candidate),"isDir":is_dir(candidate)}.stringify()) } catch(error) { print({"path":candidate,"normalized":handle.path(),"caught":true,"message":error.to_string()}.stringify()) } }\n'
 (p/'probe.f').write_text(script,encoding='utf-8');run=subprocess.run([NIFT,'probe.f','--no-process'],cwd=p,capture_output=True,text=True,encoding='utf-8');assert run.returncode==0,run.stderr
 records=[json.loads(line) for line in run.stdout.splitlines()]
 assert [r['path'] for r in records]==candidates,'Probe string transport changed candidate paths'
 for expression in ['ls("normal.mdx")','ls("directory")','ls("**")','ls("normal.mdx/**")','ls("directory/**")','ls(".hidden directory/**")','ls("normal.mdx/*")','ls("directory/*")','open("normal.mdx")','open("directory")','open_bytes("directory")','handle.open("r")']:
  (p/'isolated.f').write_text('handle := file("directory")\ntry { value := '+expression+'; print({"ok":true,"value":value}.stringify()) } catch(error) { print({"caught":true,"message":error.to_string()}.stringify()) }\n',encoding='utf-8')
  run=subprocess.run([NIFT,'isolated.f','--no-process'],cwd=p,capture_output=True,text=True,encoding='utf-8');operations.append({'expression':expression,'exitCode':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
 report={'platform':platform.system(),'node':subprocess.check_output(['node','--version'],text=True).strip(),'records':records,'operations':operations}
 target=ROOT/'investigation/followup'/('filesystem-'+platform.system()+'-'+report['node'].split('.')[0]+'.json');target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'report':str(target),'records':len(records),'operations':operations}))
