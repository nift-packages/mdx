import {createHash,randomUUID} from 'node:crypto';
import {readFile,writeFile,mkdir,rename,unlink,realpath,readdir,stat} from 'node:fs/promises';
import {resolve,relative,isAbsolute,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {runtimeRoots} from './dependencies.mjs';
const digest=value=>createHash('sha256').update(value).digest('hex');
export async function runtimeDigest(){
 const hash=createHash('sha256'),seen=new Set();
 async function walk(path){path=await realpath(path);if(seen.has(path))return;seen.add(path);const entries=await readdir(path,{withFileTypes:true});entries.sort((a,b)=>a.name.localeCompare(b.name));for(const entry of entries){const file=join(path,entry.name);const kind=entry.isSymbolicLink()?await stat(file):entry;if(kind.isDirectory())await walk(file);else if(kind.isFile()){hash.update(await realpath(file));hash.update(await readFile(file));}}}
 await walk(fileURLToPath(new URL('.',import.meta.url)));
 for(const root of runtimeRoots())await walk(root);
 hash.update(JSON.stringify({version:process.version,platform:process.platform,arch:process.arch}));hash.update(JSON.stringify(Object.entries(process.env).sort(([a],[b])=>a.localeCompare(b))));return hash.digest('hex');
}
export async function cacheKey(document,options,paths,runtime){
 const hash=createHash('sha256');hash.update(JSON.stringify({document,options,runtime}));
 for(const path of [...new Set(paths)].sort()){hash.update(path);hash.update(digest(await readFile(resolve(path))));}
 return hash.digest('hex');
}
async function directory(){const root=await realpath(process.cwd());const dir=resolve('.nift/mdx-cache');await mkdir(dir,{recursive:true});const full=await realpath(dir),rel=relative(root,full);if(rel.startsWith('..')||isAbsolute(rel))throw new Error('Cache directory escapes project');return full;}
export async function get(key){const path=join(await directory(),key+'.json');try{const full=await realpath(path),rel=relative(await directory(),full);if(rel.startsWith('..')||isAbsolute(rel))throw new Error('Cache record escapes project');const record=JSON.parse(await readFile(full,'utf8'));if(record.checksum===digest(JSON.stringify({html:record.html,dependencies:record.dependencies}))&&record.key===key&&record.version===1&&typeof record.html==='string'&&Array.isArray(record.dependencies)&&record.dependencies.every(x=>typeof x==='string'))return record;}catch{}return null;}
export async function put(key,result){const path=join(await directory(),key+'.json'),tmp=path+'.'+randomUUID()+'.tmp';try{await writeFile(tmp,JSON.stringify({version:1,key,html:result.html,dependencies:result.dependencies,checksum:digest(JSON.stringify({html:result.html,dependencies:result.dependencies}))}),{flag:'wx'});await rename(tmp,path);}finally{await unlink(tmp).catch(()=>{});}}
