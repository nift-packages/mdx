#!/usr/bin/env python3
"""Exact parser parity against the frozen original, including mixed line endings."""
import json,os,pathlib,random,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parent.parent
NIFT=os.environ.get('NIFT','/home/nick/Repositories/nift/nift/nift')
random.seed(713)
units=['text','é',' ','\t','\v','\f','\n','\r','\r\n','<A />','{value}','`code`','\\{literal}','\\<A>','~~~\ncode\n~~~\n','```js\nimport hidden\n```\n','import X from "./x.mdx"\n','export const value = 1\n']
sources=[''.join(random.choices(units,k=random.randint(2,12))) for _ in range(160)]
sources+=['plain\n\n   ~~~\ncode\n~~~\n','plain\r\n\r\nimport X from "./x.mdx"\r\n','text\n \t\nexport const x=1\n','é text\n\n<Aside>{value}</Aside>','---\r\ntitle: é\r\n---\r\nText']
with tempfile.TemporaryDirectory(prefix='mdx-parity-') as folder:
 p=pathlib.Path(folder);(p/'sources.json').write_text(json.dumps(sources))
 (p/'original.f').write_bytes(subprocess.check_output(['git','show','mdx-0.1.0-parser-baseline:src/mdx.f'],cwd=ROOT))
 outputs=[]
 for source in [p/'original.f',ROOT/'src/mdx.f']:
  (p/'compare.f').write_text('@import('+json.dumps(str(source))+')\nf := file("sources.json")\nf.open("r")\nsources := f.read_val()\nf.close()\nfor(source : sources) { print(mdx.parse(source).stringify()) }\n')
  run=subprocess.run([NIFT,'compare.f','--no-process'],cwd=p,capture_output=True,text=True,timeout=180);assert run.returncode==0,run.stderr;outputs.append(run.stdout.splitlines())
 assert len(outputs[0])==len(sources)
 for index,(before,after) in enumerate(zip(*outputs)):assert before==after,(index,sources[index],before,after)
print('PASS exact original parser parity:',len(sources),'mixed/adversarial sources')
