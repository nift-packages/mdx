#!/usr/bin/env python3
"""Full preservation corpus profile; optional isolated scanner variants."""
import collections,csv,hashlib,json,math,os,pathlib,statistics,subprocess,sys,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[2];NIFT=os.environ.get('NIFT','/home/nick/Repositories/nift/nift/nift');upstream=pathlib.Path(sys.argv[1]);variant=pathlib.Path(sys.argv[2]).resolve() if len(sys.argv)>2 else ROOT/'src/mdx.f';label=sys.argv[3] if len(sys.argv)>3 else 'baseline'
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=upstream,text=True).strip();assert commit=='7d5b69d6ba8a6630384dffc7d012431ee3ed22ec'
paths=sorted((upstream/'apps/docs/src/content/docs/docs').rglob('*.mdx'));records=[]
if os.environ.get('MDX_PROFILE_ONE'):paths=[upstream/os.environ['MDX_PROFILE_ONE']]
def count(nodes):
 result=collections.Counter()
 for node in nodes:
  result[node['type']]+=1;result['attributes']+=len(node['attributes']);result['attributeExpressions']+=sum(a['kind'] in ['expression','spread'] for a in node['attributes']);result.update(count(node['children']))
 return result
with tempfile.TemporaryDirectory(prefix='mdx-corpus-profile-') as folder:
 p=pathlib.Path(folder)
 script='@import('+json.dumps(str(variant))+')\ntrusted := mdx.with_profile("trusted")\nfor(path : '+json.dumps([str(x) for x in paths])+'){ source := open(path); watch := timer(); watch.start(); doc := trusted.parse(source); watch.stop(); print({"path":path,"milliseconds":watch.elapsed(),"document":doc}.stringify()) }\n'
 (p/'profile.f').write_text(script,encoding='utf-8');started=time.perf_counter();run=subprocess.run([NIFT,'profile.f','--no-process'],cwd=p,capture_output=True,text=True,timeout=900);assert run.returncode==0,run.stderr
 for line in run.stdout.splitlines():
  row=json.loads(line);doc=row.pop('document');path=pathlib.Path(row['path']);data=path.read_bytes();counts=count(doc['nodes']);row.update({'path':path.relative_to(upstream).as_posix(),'bytes':len(data),'lines':len(data.decode().replace('\r\n','\n').replace('\r','\n').splitlines()),'syntaxObjects':sum(v for k,v in counts.items() if k!='attributeExpressions') if doc['ok'] else None,'jsxElements':counts['jsx_element'],'expressions':counts['expression']+counts['attributeExpressions'],'imports':len(doc['imports']),'counts':dict(counts),'importRecords':[{'specifier':i['specifier'],'dependency':i['dependency'],'extension':i['extension']} for i in doc['imports']],'frontmatter':{k:v for k,v in doc['frontmatter'].items() if k in ['present','start','end']},'ok':doc['ok'],'diagnostics':doc['diagnostics'],'sourceSha256':hashlib.sha256(data).hexdigest()});records.append(row)
 records.sort(key=lambda x:x['milliseconds'],reverse=True);values=sorted(r['milliseconds'] for r in records);total=sum(values)
 percentile=lambda p:values[min(len(values)-1,math.ceil(p*len(values))-1)]
 shares={str(p):{'pages':math.ceil(len(values)*p/100),'milliseconds':sum(x['milliseconds'] for x in records[:math.ceil(len(values)*p/100)]),'percentOfTotal':100*sum(x['milliseconds'] for x in records[:math.ceil(len(values)*p/100)])/total} for p in [1,5,10,20]}
 report={'upstreamCommit':commit,'variant':label,'scannerSha256':hashlib.sha256(variant.read_bytes()).hexdigest(),'scope':'pure trusted parse, one Nift invocation, timer excludes reads and result serialization','wallSeconds':time.perf_counter()-started,'pages':len(records),'accepted':sum(r['ok'] for r in records),'totalMilliseconds':total,'medianMilliseconds':statistics.median(values),'p90Milliseconds':percentile(.90),'p95Milliseconds':percentile(.95),'p99Milliseconds':percentile(.99),'worstShares':shares,'records':records}
 target=ROOT/'investigation/followup'/('corpus-'+label+'.json');target.write_text(json.dumps(report,indent=2)+'\n');
 with target.with_suffix('.csv').open('w',newline='') as f:
  writer=csv.DictWriter(f,lineterminator='\n',fieldnames=['path','bytes','lines','syntaxObjects','jsxElements','expressions','imports','milliseconds','ok']);writer.writeheader();writer.writerows({k:r[k] for k in writer.fieldnames} for r in records)
 print(json.dumps({k:v for k,v in report.items() if k!='records'}))
