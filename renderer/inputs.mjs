import {realpath,readFile,stat} from 'node:fs/promises';
import {resolve,relative,isAbsolute} from 'node:path';
export class Inputs{
 constructor(){this.files=new Set();}
 async track(path){
  if(typeof path!=='string'||!path)throw new Error('Rendering dependencies must be non-empty local paths');
  const root=await realpath(process.cwd()),full=await realpath(resolve(root,path)),rel=relative(root,full);
  if(rel.startsWith('..')||isAbsolute(rel))throw new Error('Rendering dependency escapes project: '+path);
  if(!(await stat(full)).isFile())throw new Error('Rendering dependency is not a file: '+path);
  this.files.add(rel.replaceAll('\\','/'));return full;
 }
 async read(path){return readFile(await this.track(path),'utf8');}
 list(){return [...this.files].sort();}
}
