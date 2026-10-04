import {createRequire} from 'node:module';
import {readFile} from 'node:fs/promises';
import {dirname, join, resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
export const pins = {'@mdx-js/mdx':'3.1.1',react:'19.3.0','react-dom':'19.3.0','remark-gfm':'4.0.1','rehype-slug':'6.0.0',acorn:'8.18.0','source-map':'0.7.6'};
const local=createRequire(import.meta.url);
const explicit=process.env.MDX_NODE_MODULES ? createRequire(join(resolve(process.env.MDX_NODE_MODULES),'__mdx__.cjs')) : null;
export async function load(specifier) {
 const name=specifier.startsWith('@')?specifier.split('/').slice(0,2).join('/'):specifier.split('/')[0];
 let filename;
 if(name==='acorn'||name==='source-map'){let owner;try{owner=local.resolve('@mdx-js/mdx');}catch{owner=explicit?.resolve('@mdx-js/mdx');}if(!owner)throw new Error('Missing MDX runtime for locked Acorn dependency');filename=createRequire(owner).resolve(specifier);}
 else try { filename=local.resolve(specifier); } catch(error) {
  if(!explicit) throw new Error(`Missing ${name}: run npm ci --ignore-scripts in the renderer directory or explicitly set MDX_NODE_MODULES for pinned global packages`);
  filename=explicit.resolve(specifier);
 }
 let dir=dirname(filename), pkg;
 while(true){try {const data=JSON.parse(await readFile(join(dir,'package.json'),'utf8'));if(data.name===name){pkg=data;break;}}catch{}const parent=dirname(dir);if(parent===dir)break;dir=parent;}
 if(!pkg || pkg.version!==pins[name]) throw new Error(`Dependency version mismatch: ${name}; expected ${pins[name]}, found ${pkg?.version}`);
 return import(pathToFileURL(filename).href);
}
export async function probe() {for(const name of Object.keys(pins))await load(name);return pins;}
if(process.argv[2]==='--check'){try{console.log(JSON.stringify({ok:true,versions:await probe()}));}catch(e){console.error(e.message);process.exitCode=1;}}
