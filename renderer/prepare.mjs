// Explicit trusted render-only preparation. Preservation APIs are unchanged.
import {readFile,writeFile,mkdir,realpath,stat,unlink} from 'node:fs/promises';
import {resolve,relative,isAbsolute,dirname} from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {Worker} from 'node:worker_threads';
import {Inputs} from './inputs.mjs';
import {runtimeDigest} from './cache.mjs';
import {validate,LIMITS} from './protocol.mjs';
import {replace} from './atomic.mjs';
const hash=value=>createHash('sha256').update(value).digest('hex');
async function atomic(path,record){await mkdir(dirname(path),{recursive:true});const root=await realpath(process.cwd()),parent=await realpath(dirname(path));const rel=relative(root,parent);if(rel.startsWith('..')||isAbsolute(rel))throw new Error('Prepared output escapes project');try{if(await readFile(path,'utf8')===JSON.stringify(record))return;}catch(error){if(error.code!=='ENOENT')throw error;}const temp=path+'.'+randomUUID()+'.tmp';try{await writeFile(temp,JSON.stringify(record),{flag:'wx'});await replace(temp,path);}finally{await unlink(temp).catch(()=>{});}}
async function fingerprints(references,memo=new Map()){const inputs=new Inputs(),rows=[];for(const row of references){const canonical=await inputs.track(row.requested);if(!memo.has(canonical))memo.set(canonical,hash(await readFile(canonical)));rows.push({requested:row.requested,canonical:relative(process.cwd(),canonical).replaceAll('\\','/'),sha256:memo.get(canonical)??hash(await readFile(canonical))});}return rows;}
async function batch(request){validate(request);return new Promise((yes,no)=>{const worker=new Worker(new URL('./worker.mjs',import.meta.url),{workerData:request,resourceLimits:{maxOldGenerationSizeMb:512}});let done=false;const finish=(error,result)=>{if(done)return;done=true;clearTimeout(timer);worker.terminate();error?no(error):yes(result);};const timer=setTimeout(()=>finish(new Error('Render preparation deadline exceeded')),request.options.timeoutMs??120000);worker.once('message',x=>finish(null,x));worker.once('error',x=>finish(x));worker.once('exit',code=>{if(!done)finish(new Error('Renderer exited before response: '+code));});});}
export async function preparePaths(paths,options){
 if(options?.policy!=='trusted')throw new Error('Render preparation requires explicit trusted policy');
 if(!Array.isArray(paths)||!paths.length||paths.length>LIMITS.documents||new Set(paths).size!==paths.length)throw new Error('Invalid render preparation paths');
 if(options.timeoutMs!==undefined&&(!Number.isInteger(options.timeoutMs)||options.timeoutMs<1||options.timeoutMs>600000))throw new Error('Invalid renderer deadline');
 const inputs=new Inputs(),runtime=await runtimeDigest(),pending=[],results=[],records=new Map(),memo=new Map();
 for(const path of paths){if(typeof path!=='string'||isAbsolute(path)||path.split(/[\\/]/).includes('..'))throw new Error('Preparation paths must be project-relative');const full=await inputs.track(path),source=await inputs.read(full),normalized=relative(process.cwd(),resolve(path)).replaceAll('\\','/');const output=resolve('.nift/mdx-prepared',normalized+'.json');await mkdir(dirname(output),{recursive:true});const project=await realpath(process.cwd()),parent=await realpath(dirname(output));if(relative(project,parent).startsWith('..'))throw new Error('Prepared cache escapes project');let old;try{const fullOutput=await realpath(output);if(relative(project,fullOutput).startsWith('..'))throw new Error('Prepared record escapes project');old=JSON.parse(await readFile(output,'utf8'));}catch(error){if(error.code!=='ENOENT'&&!(error instanceof SyntaxError))throw error;}
  let hit=false;if(old?.version===1&&old.source===source&&JSON.stringify(old.options)===JSON.stringify(options)&&old.runtime===runtime&&old.checksum===hash(old.html)&&Array.isArray(old.fingerprints)){try{hit=JSON.stringify(await fingerprints(old.fingerprints,memo))===JSON.stringify(old.fingerprints);}catch{hit=false;}}
  if(hit){results.push({id:normalized,ok:true,cacheHit:true,dependencies:old.dependencies});continue;}
  pending.push({id:normalized,path:normalized,source,dependencies:[]});records.set(normalized,{output,source});
 }
 if(pending.length){const response=await batch({version:1,documents:pending,options:{...options,cache:false,discovery:'compiler'}});if(!response.ok)throw new Error(JSON.stringify(response));if(response.results.some(x=>!x.ok))throw new Error(JSON.stringify(response.results.filter(x=>!x.ok)));
  memo.clear();for(const result of response.results){for(const observed of result.observations??[]){if(hash(await readFile(observed.path))!==observed.sha256)throw new Error('Dependency changed during preparation: '+observed.path);}const item=records.get(result.id),refs=result.references??result.dependencies.map(path=>({requested:path}));if(!refs.some(x=>x.requested===result.id))refs.push({requested:result.id});const checks=await fingerprints(refs,memo);if(hash(await inputs.read(result.id))!==hash(item.source))throw new Error('Source changed during preparation: '+result.id);const record={version:1,source:item.source,options,runtime,html:result.html,checksum:hash(result.html),dependencies:[...new Set([...result.dependencies,...checks.flatMap(x=>[x.requested,x.canonical])])].sort(),fingerprints:checks};await atomic(item.output,record);results.push(result);}
 }
 return {version:1,ok:true,prepared:pending.length,cached:paths.length-pending.length,results};
}
if(process.argv[1]&&await realpath(process.argv[1])===fileURLToPath(import.meta.url)){try{const request=JSON.parse(await readFile(process.argv[2],'utf8'));console.log(JSON.stringify(await preparePaths(request.paths,request.options)));}catch(error){console.error(error.message);process.exitCode=1;}}
