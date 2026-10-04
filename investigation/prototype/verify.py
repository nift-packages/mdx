import os
import subprocess,json,pathlib
P=pathlib.Path(__file__).resolve().parent
NIFT=os.environ.get('NIFT', '/home/nick/Repositories/nift/nift/nift')
r=subprocess.run([NIFT,'demo.f'],cwd=P,capture_output=True,text=True,check=True)
doc=json.loads(r.stdout.splitlines()[0]);html='\n'.join(r.stdout.splitlines()[1:])
assert doc['ok'] and [x['path'] for x in doc['dependencies']]==['fixtures/shared.mdx','fixtures/nested.mdx']
assert '<aside data-type="warning">' in html and 'Transitive <em>content</em>' in html
assert 'title: Demonstration' not in html and '<script' not in html
(P/'demo.html').write_text(html.rstrip()+'\n')
(P/'demo-document.json').write_text(json.dumps(doc,indent=2)+'\n')
for source,success in [('# Plain\n\nHello.',True),('<Unknown />',False),('<Aside',False),('{1 + 2}',True)]:
 request={'ok':True,'source':source,'path':None,'dependencies':[]}
 out=subprocess.run(['node','helper.mjs',json.dumps(request)],cwd=P,capture_output=True,text=True)
 result=json.loads(out.stdout);assert result['ok']==success,(source,result)
blocked=subprocess.run([NIFT,'demo.f','--no-process'],cwd=P,capture_output=True,text=True)
assert blocked.returncode!=0 and 'execution disabled' in blocked.stdout+blocked.stderr
print('PASS: Nift composition, transitive imports, Markdown, Aside, frontmatter, plain HTML, unknown/malformed failures, trusted expression and process denial')
