#!/usr/bin/env python3
"""Compare preservation imports with compiler AST discovery on existing corpora."""
import ast,json,os,pathlib,random,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2];NIFT=os.environ.get('NIFT','/home/nick/Repositories/nift/nift/nift')
tree=ast.parse((ROOT/'tests/test_mdx.py').read_text());literal=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='corpus' for t in n.targets));sources=eval(compile(ast.Expression(literal),'fixture literals','eval'),{'__builtins__':{}})
for i in range(80):sources.append(('m'*(i%7))+'{a'+(' + {b: 1}'*(i%5))+'}'+('<X a="}>">y</X>' if i%3==0 else '`<Z />`')+'\n')
# Existing seeded golden corpus.
random.seed(713);units=['text','é',' ','\t','\v','\f','\n','\r','\r\n','<A />','{value}','`code`','\\{literal}','\\<A>','~~~\ncode\n~~~\n','```js\nimport hidden\n```\n','import X from "./x.mdx"\n','export const value = 1\n']
sources += [''.join(random.choices(units,k=random.randint(2,12))) for _ in range(160)]
sources += ['plain\n\n   ~~~\ncode\n~~~\n','plain\r\n\r\nimport X from "./x.mdx"\r\n','text\n \t\nexport const x=1\n','é text\n\n<Aside>{value}</Aside>','---\r\ntitle: é\r\n---\r\nText']
# All literal .mdx import/graph fixtures from the existing integration suite.
for n in ast.walk(tree):
 if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='write' and len(n.args)==2 and isinstance(n.args[0],ast.BinOp) and isinstance(n.args[0].right,ast.Constant) and str(n.args[0].right.value).endswith('.mdx') and isinstance(n.args[1],ast.Constant):sources.append(n.args[1].value)
sources += ['~~~mdx\nimport X from "./hidden.mdx"\n~~~\n','`import X from "./hidden.mdx"`\n','{"import X from \'./hidden.mdx\'"}\n','{/* import X from "./hidden.mdx" */}\n','export const text = `import X from "./hidden.mdx"`\n','export const text = `template ${"import ./hidden.mdx"}`\n','<A label={"import ./hidden.mdx"} />\n','import A from "./a.mdx"\n\nimport B from "./b.md"\n\n<A />\n','{import("./dynamic.mdx")}\n','export {x} from "./reexport.mdx"\n']
with tempfile.TemporaryDirectory(prefix='mdx-dep-fixtures-') as folder:
 p=pathlib.Path(folder)
 for i,source in enumerate(sources):(p/f'fixture-{i}.mdx').write_bytes(source.encode('utf-8'))
 (p/'paths.json').write_text(json.dumps([f'fixture-{i}.mdx' for i in range(len(sources))]))
 (p/'sources.json').write_text(json.dumps(sources,ensure_ascii=False),encoding='utf-8');(p/'parser.f').write_text('@import('+json.dumps(str(ROOT/'src/mdx.f'))+')\nf := file("paths.json"); f.open("r"); paths := f.read_val(); f.close()\nfor(path : paths){ source := open(path); doc := mdx.parse(source); print({"ok":doc.ok,"imports":doc.imports,"source":doc.source}.stringify()) }\n');run=subprocess.run([NIFT,'parser.f','--no-process'],cwd=p,capture_output=True,text=True,timeout=180);assert run.returncode==0,run.stderr;preserved=[json.loads(x) for x in run.stdout.splitlines()]
 (p/'scan.mjs').write_text('import {scan} from '+json.dumps((ROOT/'investigation/followup/dependency_audit.mjs').as_uri())+';import {readFileSync} from "node:fs";for(const source of JSON.parse(readFileSync("sources.json"))){try{console.log(JSON.stringify({ok:true,...scan(source)}))}catch(error){console.log(JSON.stringify({ok:false,message:error.message}))}}');env=os.environ.copy();env.setdefault('MDX_NODE_MODULES','/usr/local/lib/node_modules');run=subprocess.run(['node','scan.mjs','--fixtures'],cwd=p,env=env,capture_output=True,text=True,timeout=60);assert run.returncode==0,run.stderr;semantic=[json.loads(x) for x in run.stdout.splitlines()]
 records=[]
 for i,(left,right) in enumerate(zip(preserved,semantic)):
  before=[{'specifier':x['specifier'],'dependency':x['dependency']} for x in left['imports']];after=right.get('imports',[]);records.append({'index':i,'sourceTransportEqual':left.get('source')==sources[i], 'preservationSource':left.get('source'),'preservationAccepted':left['ok'],'compilerAccepted':right['ok'],'importsEqual':before==after if left['ok'] and right['ok'] else None,'preservationImports':before,'compilerImports':after,'compilerUnsupported':right.get('unsupported',[]),'compilerError':right.get('message'),'source':sources[i]})
 report={'fixtures':len(sources),'jointlyAccepted':sum(x['preservationAccepted'] and x['compilerAccepted'] for x in records),'importMismatches':[x for x in records if x['importsEqual'] is False],'compilerRejects':sum(not x['compilerAccepted'] for x in records),'records':records};(ROOT/'investigation/followup/dependency-fixtures.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='records'}))
