import {replace} from './atomic.mjs';
import {createHash,randomUUID} from 'node:crypto';
import {readFile,writeFile,mkdir,unlink,realpath,readdir,stat} from 'node:fs/promises';
import {resolve,relative,isAbsolute,join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {runtimeRoots} from './dependencies.mjs';
const digest=value=>createHash('sha256').update(value).digest('hex');
export async function runtimeDigest(){
 const hash=createHash('sha256'),seen=new Set();
 async function walk(path){path=await realpath(path);if(seen.has(path))return;seen.add(path);const entries=await readdir(path,{withFileTypes:true});entries.sort((a,b)=>a.name.localeCompare(b.name));for(const entry of entries){const file=join(path,entry.name);const kind=entry.isSymbolicLink()?await stat(file):entry;if(kind.isDirectory())await walk(file);else if(kind.isFile()){hash.update(await realpath(file));hash.update(await readFile(file));}}}
 await walk(fileURLToPath(new URL('.',import.meta.url)));
 const packages=new Set();
 async function packageTree(root){
  root=await realpath(root);if(packages.has(root))return;packages.add(root);await walk(root);
  const pkg=JSON.parse(await readFile(join(root,'package.json'),'utf8'));
  for(const name of Object.keys({...pkg.dependencies,...pkg.optionalDependencies,...pkg.peerDependencies}).sort()){
   let found;
   try{let cursor=dirname(createRequire(join(root,'package.json')).resolve(name));while(true){try{const candidate=JSON.parse(await readFile(join(cursor,'package.json'),'utf8'));if(candidate.name){found=cursor;break;}}catch{}const parent=dirname(cursor);if(parent===cursor)break;cursor=parent;}}catch{}
   if(!found){let cursor=root;while(true){const candidate=join(cursor,'node_modules',...name.split('/'));try{await stat(join(candidate,'package.json'));found=candidate;break;}catch{}const parent=dirname(cursor);if(parent===cursor)break;cursor=parent;}}
   if(found)await packageTree(found);
  }
 }
 for(const root of runtimeRoots())await packageTree(root);
 hash.update(JSON.stringify({version:process.version,platform:process.platform,arch:process.arch}));hash.update(JSON.stringify(Object.entries(process.env).sort(([a],[b])=>a.localeCompare(b))));return hash.digest('hex');
}
export async function cacheKey(document,options,paths,runtime){
 const hash=createHash('sha256');hash.update(JSON.stringify({document,options,runtime}));
 for(const path of [...new Set(paths)].sort()){hash.update(path);hash.update(digest(await readFile(resolve(path))));}
 return hash.digest('hex');
}
async function directory(){const root=await realpath(process.cwd());const dir=resolve('.nift/mdx-cache');await mkdir(dir,{recursive:true});const full=await realpath(dir),rel=relative(root,full);if(rel.startsWith('..')||isAbsolute(rel))throw new Error('Cache directory escapes project');return full;}
export async function get(key){const path=join(await directory(),key+'.json');try{const full=await realpath(path),rel=relative(await directory(),full);if(rel.startsWith('..')||isAbsolute(rel))throw new Error('Cache record escapes project');if((await stat(full)).size>64*1024*1024)return null;const record=JSON.parse(await readFile(full,'utf8'));if(record.checksum===digest(JSON.stringify({html:record.html,dependencies:record.dependencies}))&&record.key===key&&record.version===1&&typeof record.html==='string'&&Array.isArray(record.dependencies)&&record.dependencies.every(x=>typeof x==='string'))return record;}catch{}return null;}
export async function put(key,result){const path=join(await directory(),key+'.json'),tmp=path+'.'+randomUUID()+'.tmp';const serialized=JSON.stringify({version:1,key,html:result.html,dependencies:result.dependencies,checksum:digest(JSON.stringify({html:result.html,dependencies:result.dependencies}))});if(Buffer.byteLength(serialized)>64*1024*1024)throw new Error('Cache record exceeds 64MiB');try{await writeFile(tmp,serialized,{flag:'wx'});await replace(tmp,path);}finally{await unlink(tmp).catch(()=>{});}}
