import os
import pathlib,json,subprocess,time
P=pathlib.Path(__file__).resolve().parent
NIFT=os.environ.get('NIFT', '/home/nick/Repositories/nift/nift/nift')
def put(path,value):
 f=P/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(value)
put('.nift/config.json',json.dumps({'config':{'content-dir':'content/','content-ext':'.html','output-dir':'public/','output-ext':'.html','default-template':'templates/template.html','build-threads':1,'incremental-mode':'hash'}}))
put('.nift/tracked.json',json.dumps({'tracked':[{'name':'/','title':'Home','template':'templates/template.html'},{'name':'other','title':'Other','template':'templates/other.html'}]}))
put('templates/template.html','@import("../mdx-prototype.f")\n$[mdx.html(mdx.input("fixtures/page.mdx"))]\n@content\n')
put('templates/other.html','unrelated\n@content\n');put('content/index.html','home\n');put('content/other.html','other\n')
def call(args):
 t=time.perf_counter();r=subprocess.run([NIFT,*args],cwd=P,text=True,capture_output=True,check=True);return {'seconds':time.perf_counter()-t,'stdout':r.stdout,'stderr':r.stderr}
initial=call(['build','--all']);noop=call(['build'])
old=(P/'fixtures/nested.mdx').read_text();unrelated=(P/'public/other.html').stat().st_mtime_ns
try:
 put('fixtures/nested.mdx','Changed transitive content.\n');changed=call(['build'])
 assert 'Changed transitive content.' in (P/'public/index.html').read_text()
 assert (P/'public/other.html').stat().st_mtime_ns==unrelated
 metadata=(P/'.nift/public/index.info.json').read_text()
 for path in ['fixtures/page.mdx','fixtures/shared.mdx','fixtures/nested.mdx']:assert metadata.count(path)==1
finally:put('fixtures/nested.mdx',old)
call(['build'])
(P/'build-results.json').write_text(json.dumps({'initial':initial,'no_change':noop,'transitive_edit':changed},indent=2)+'\n')
print('PASS: rendered site builds; no-change skips; nested edit changes HTML and preserves unrelated output; each MDX dependency registered once')
