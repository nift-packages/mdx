import {Worker} from 'node:worker_threads';
import {readFile,writeFile,rename,unlink,mkdir,realpath,stat} from 'node:fs/promises';
import {resolve,dirname,relative,isAbsolute} from 'node:path';
import {VERSION,LIMITS,validate,diagnostic} from './protocol.mjs';
import {randomUUID} from 'node:crypto';
async function confined(path){const root=await realpath(process.cwd());const full=resolve(root,path);const rel=relative(root,full);if(rel.startsWith('..') || isAbsolute(rel))throw new Error('Protocol paths must stay inside project');const parent=await realpath(dirname(full));const p=relative(root,parent);if(p.startsWith('..') || isAbsolute(p))throw new Error('Protocol path symlink escapes project');return full;}
async function atomic(path,value){const data=JSON.stringify(value);if(Buffer.byteLength(data)>LIMITS.responseBytes)throw new Error('Response transport limit exceeded');const tmp=path+'.'+randomUUID()+'.tmp';try{await writeFile(tmp,data,{flag:'wx'});await rename(tmp,path);}finally{await unlink(tmp).catch(()=>{});}}
let responsePath;
try{
 const argv=process.argv.slice(2);if(argv.length!==4 || argv[0]!=='--request' || argv[2]!=='--response')throw new Error('Usage: node cli.mjs --request request.json --response response.json');
 responsePath=await confined(argv[3]);const requestPath=await confined(argv[1]);await confined(await realpath(requestPath));if((await stat(requestPath)).size>LIMITS.requestBytes)throw new Error('Request transport limit exceeded');
 const request=validate(JSON.parse(await readFile(requestPath,'utf8')));
 const timeout=request.options.timeoutMs??120000;if(!Number.isInteger(timeout)||timeout<1||timeout>600000)throw new Error('timeoutMs must be 1..600000');
 const response=await new Promise(resolveResult=>{
  const worker=new Worker(new URL('./worker.mjs',import.meta.url),{workerData:request,resourceLimits:{maxOldGenerationSizeMb:512}});let complete=false;
  const finish=value=>{if(complete)return;complete=true;clearTimeout(timer);worker.terminate();resolveResult(value);};
  const timer=setTimeout(()=>finish({version:VERSION,ok:false,diagnostics:[diagnostic('process','timeout','Renderer deadline exceeded')]}),timeout);
  worker.once('message',finish);worker.once('error',error=>finish({version:VERSION,ok:false,diagnostics:[diagnostic('process','worker_error',error.message)]}));
  worker.once('exit',code=>{if(!complete)finish({version:VERSION,ok:false,diagnostics:[diagnostic('process','worker_exit','Renderer exited before producing a response: '+code)]});});
 });
 response.ok=response.ok && response.results.every(result=>result.ok);if(response.ok){
   for(let index=0;index<request.documents.length;index++){
    const document=request.documents[index],result=response.results[index];
    if(document.path!==null){
     const output=resolve('.nift/mdx-html',document.path+'.json');
     const base=resolve('.nift/mdx-html');const rel=relative(base,output);if(rel.startsWith('..')||isAbsolute(rel))throw new Error('Prepared output path escapes project');
     await mkdir(dirname(output),{recursive:true});await confined(output);
     const record={source:document.source,options:request.options,html:result.html,dependencies:result.dependencies};
     const serialized=JSON.stringify(record);let previous;try{previous=await readFile(output,'utf8');}catch{}
     if(serialized!==previous)await atomic(output,record);
    }
   }
  }
  await atomic(responsePath,response);if(!response.ok)process.exitCode=1;
}catch(error){const response={version:VERSION,ok:false,diagnostics:[diagnostic('transport','invalid_request',error.message)]};if(responsePath)await atomic(responsePath,response);else console.error(error.message);process.exitCode=1;}
