#!/usr/bin/env python3
"""Helper-only real-corpus compatibility audit; deliberately not certification."""
import collections,hashlib,json,os,pathlib,re,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
upstream=pathlib.Path(sys.argv[1]);commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=upstream,text=True).strip();expected='7d5b69d6ba8a6630384dffc7d012431ee3ed22ec';assert commit==expected
docs=upstream/'apps/docs/src/content/docs/docs';canonical=sorted(docs.rglob('*.mdx'));paths=canonical+sorted(docs.rglob('*.md'))+sorted((upstream/'apps/web/src/content/blog/en').glob('*.mdx'));documents=[];imports=collections.Counter();provenance=[];components=collections.defaultdict(list)
for path in paths:
 data=path.read_bytes();source=data.decode('utf-8');name=path.relative_to(upstream).as_posix();documents.append({'id':name,'path':name,'source':source,'dependencies':[]});provenance.append({'path':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
 lines=[];fence=None
 for line in source.splitlines():
  marker=re.match(r'^\s*(`{3,}|~{3,})',line)
  if marker:
   if fence is None:fence=marker.group(1)[0]
   elif marker.group(1)[0]==fence:fence=None
   continue
  if fence is None:lines.append(line)
 authored='\n'.join(lines)
 for spec in re.findall(r'^import\s+[^;]*?\bfrom\s+[\'"]([^\'"]+)',authored,re.M):imports[spec]+=1
 for component in ['Steps','Card','CardGrid','LinkCard','Tabs','TabItem','Code','FileTree','PackageManagers','MermaidGraph','YouTubeEmbed','BuildCredentialsQuestionnaire','ConditionalQuestionnaire','BlogMidArticleCta']:
  if re.search(r'<'+component+r'\b',authored):components[component].append(name)
request=upstream/'.nift-mdx-gate-request.json';response=upstream/'.nift-mdx-gate-response.json';request.write_text(json.dumps({'version':1,'documents':documents,'options':{'policy':'trusted','timeoutMs':600000}}))
env=os.environ.copy();env.setdefault('MDX_NODE_MODULES','/usr/local/lib/node_modules')
try:
 run=subprocess.run(['node',str(ROOT/'renderer/cli.mjs'),'--request',request.name,'--response',response.name],cwd=upstream,env=env,capture_output=True,text=True,timeout=600);result=json.loads(response.read_text());rows=result.get('results',[]);counts=collections.Counter();failures=[];success=[]
 for row in rows:
  if row['ok']:success.append({'path':row['id'],'htmlSha256':hashlib.sha256(row['html'].encode()).hexdigest(),'htmlBytes':len(row['html'].encode())})
  else:
   failures.append({'path':row['id'],'diagnostics':row['diagnostics']})
   for d in row['diagnostics']:counts[d['code']]+=1
 report={'upstreamCommit':commit,'canonicalMdxPages':len(canonical),'totalFixtures':len(paths),'componentFixturePaths':dict(components),'scope':'helper-only default pipeline, no project adapters; does not override parser rejection or certify visual/interactive parity','exitCode':run.returncode,'accepted':len(success),'failed':len(failures),'globalDiagnostics':result.get('diagnostics',[]),'diagnosticCounts':dict(counts),'imports':dict(imports),'provenance':provenance,'successfulOutputs':success,'failures':failures}
 (ROOT/'investigation/checkpoints/CP22-corpus-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['canonicalMdxPages','accepted','failed','diagnosticCounts','globalDiagnostics']}))
finally:
 request.unlink(missing_ok=True);response.unlink(missing_ok=True)
