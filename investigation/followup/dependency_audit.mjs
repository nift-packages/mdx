// Investigation only: compiler AST dependency scan, no evaluation or production API.
import {load} from '../../renderer/dependencies.mjs';
import {body} from '../../renderer/source.mjs';
import {readFile,writeFile,readdir} from 'node:fs/promises';
import {resolve,relative,extname} from 'node:path';
import {performance} from 'node:perf_hooks';
import {createHash} from 'node:crypto';
const {createProcessor,compile}=await load('@mdx-js/mdx');
const remarkGfm=(await load('remark-gfm')).default;
const root=resolve(process.argv[2]??'.');const processor=createProcessor({remarkPlugins:[remarkGfm]});
async function files(dir){const result=[];for(const e of await readdir(dir,{withFileTypes:true})){const p=resolve(dir,e.name);if(e.isDirectory())result.push(...await files(p));else if(e.name.endsWith('.mdx'))result.push(p);}return result.sort();}
export function scan(source){
 const prepared=body({source}),ast=processor.parse(prepared.value),imports=[],exports=[],unsupported=new Set();
 function inspect(node){
  if(!node||typeof node!=='object')return;
  if(node.type==='ImportDeclaration'){const spec=node.source.value;imports.push({specifier:spec,dependency:(spec.startsWith('./')||spec.startsWith('../'))&&['.md','.mdx'].includes(extname(spec))&&!spec.includes('?')&&!spec.includes('#')});}
  if((node.type==='ExportNamedDeclaration'||node.type==='ExportAllDeclaration')&&node.source){exports.push(node.source.value);unsupported.add('document_reexport');}
  if(node.type==='ImportExpression')unsupported.add('dynamic_import');
  for(const [key,value] of Object.entries(node))if(key!=='position'&&key!=='loc'){if(Array.isArray(value))for(const child of value)inspect(child);else if(value&&typeof value==='object')inspect(value);}
 }
 inspect(ast);return {imports,exports,unsupported:[...unsupported],lineOffset:prepared.lineOffset};
}
if(process.argv[2]!== '--fixtures'){
let commit=(await readFile(resolve(root,'.git/HEAD'),'utf8')).trim();if(commit.startsWith('ref: ')){const ref=commit.slice(5);try{commit=(await readFile(resolve(root,'.git',ref),'utf8')).trim();}catch{const line=(await readFile(resolve(root,'.git/packed-refs'),'utf8')).split('\n').find(x=>x.endsWith(' '+ref));if(!line)throw new Error('Missing Git ref');commit=line.split(' ')[0];}}if(commit!=='7d5b69d6ba8a6630384dffc7d012431ee3ed22ec')throw new Error('Unexpected upstream commit');
const canonical=await files(resolve(root,'apps/docs/src/content/docs/docs'));const blogs=await files(resolve(root,'apps/web/src/content/blog/en'));const records=[];const started=performance.now();for(const path of [...canonical,...blogs]){const source=await readFile(path,'utf8');const t=performance.now();try{const result=scan(source);const milliseconds=performance.now()-t;const c=performance.now();await compile({value:body({source}).value,path},{outputFormat:'function-body',remarkPlugins:[remarkGfm]});records.push({path:relative(root,path).replaceAll('\\','/'),sourceSha256:createHash('sha256').update(source).digest('hex'),milliseconds,compileMilliseconds:performance.now()-c,...result});}catch(error){records.push({path:relative(root,path),error:error.message,milliseconds:performance.now()-t});}}
const report={upstreamCommit:commit,canonicalMdxPages:canonical.length,blogMdxPages:blogs.length,scope:'isolated MDX compiler AST scan and compilation; no evaluation, no Nift @dep registration, no production API',pages:records.length,wallMilliseconds:performance.now()-started,totalScanMilliseconds:records.reduce((s,r)=>s+r.milliseconds,0),totalCompileMilliseconds:records.reduce((s,r)=>s+(r.compileMilliseconds??0),0),records};await writeFile(new URL('dependency-audit.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({pages:report.pages,wallMilliseconds:report.wallMilliseconds,totalScanMilliseconds:report.totalScanMilliseconds,totalCompileMilliseconds:report.totalCompileMilliseconds,failures:records.filter(r=>r.error).length}));

}
