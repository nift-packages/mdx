import {realpath,readFile,stat} from 'node:fs/promises';
import {load} from './dependencies.mjs';
import {resolve,relative,isAbsolute,dirname} from 'node:path';
export class Inputs{
 constructor(){this.files=new Set();}
 async track(path){
  if(typeof path!=='string'||!path)throw new Error('Rendering dependencies must be non-empty local paths');
  const root=await realpath(process.cwd()),full=await realpath(resolve(root,path)),rel=relative(root,full);
  if(rel.startsWith('..')||isAbsolute(rel))throw new Error('Rendering dependency escapes project: '+path);
  if(!(await stat(full)).isFile())throw new Error('Rendering dependency is not a file: '+path);
  this.files.add(rel.replaceAll('\\','/'));return full;
 }
 async read(path){const full=await this.track(path);if((await stat(full)).size>256*1024)throw new Error('Rendering source exceeds 256KiB');return readFile(full,'utf8');}
 async module(path,visited=new Set()){
  const full=await this.track(path);if(visited.has(full))return full;visited.add(full);
  if(visited.size>256)throw new Error('Adapter module graph exceeds 256 files');
  const {parse}=await load('acorn');const ast=parse(await this.read(full),{ecmaVersion:'latest',sourceType:'module'});
  function inspect(node){if(!node||typeof node!=='object')return;if(node.type==='ImportExpression'||(node.type==='CallExpression'&&node.callee?.name==='require'))throw new Error('Dynamic import/require is unsupported in adapter modules');for(const [key,value] of Object.entries(node))if(key!=='loc'){if(Array.isArray(value))value.forEach(inspect);else if(value&&typeof value==='object')inspect(value);}}
  inspect(ast);
  for(const statement of ast.body){
   if(!statement.source)continue;const spec=statement.source.value;
   if(spec.startsWith('node:'))continue;
   if(!spec.startsWith('.'))throw new Error('Adapter package imports require an explicit local module boundary: '+spec);
   await this.module(resolve(dirname(full),spec),visited);
  }
  return full;
 }
 list(){return [...this.files].sort();}
}
