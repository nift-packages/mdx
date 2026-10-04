import {load} from './dependencies.mjs';
import {diagnostic} from './protocol.mjs';
import {Inputs} from './inputs.mjs';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {resolve,dirname,extname,relative,isAbsolute} from 'node:path';
import {body,originalLocation} from './source.mjs';
import {realpath} from 'node:fs/promises';
import * as cache from './cache.mjs';
import {performance} from 'node:perf_hooks';
const {compile,run}=await load('@mdx-js/mdx');
const runtime=await load('react/jsx-runtime');
const React=(await load('react')).default;
const {renderToStaticMarkup}=await load('react-dom/server');
const remarkGfm=(await load('remark-gfm')).default;
const {SourceMapGenerator,SourceMapConsumer}=await load('source-map');
const rehypeSlug=(await load('rehype-slug')).default;
function walk(node,callback){if(!node||typeof node!=='object')return;callback(node);for(const [key,value] of Object.entries(node))if(key!=='loc'&&key!=='position'){if(Array.isArray(value))for(const child of value)walk(child,callback);else if(value&&typeof value==='object')walk(value,callback);}}
function importBinding(statement){
 const declarations=statement.specifiers.map(spec=>{
  const slot={type:'MemberExpression',computed:true,object:{type:'MemberExpression',computed:false,object:{type:'MemberExpression',computed:true,object:{type:'Identifier',name:'arguments'},property:{type:'Literal',value:0}},property:{type:'Identifier',name:'imports'}},property:{type:'Literal',value:statement.source.value}};
  const init=spec.type==='ImportNamespaceSpecifier'?slot:{type:'MemberExpression',computed:true,object:slot,property:{type:'Literal',value:spec.type==='ImportDefaultSpecifier'?'default':spec.imported.name??spec.imported.value}};
  return {type:'VariableDeclarator',id:spec.local,init};
 });
 return declarations.length?{type:'VariableDeclaration',kind:'const',declarations}:null;
}
export async function renderBatch(request){
 const projectRoot=await realpath(process.cwd());
 const shared=new Inputs();let components={};const mappedImports={};
 for(const path of request.options.dependencies??[])await shared.track(path);
 const packageRoot=dirname(fileURLToPath(import.meta.url));
 for(const name of ['cli.mjs','worker.mjs','render.mjs','inputs.mjs','source.mjs','dependencies.mjs','protocol.mjs','cache.mjs','atomic.mjs','prepare.mjs','package-lock.json']){
  const path=resolve(packageRoot,name),rel=relative(projectRoot,path);if(rel.startsWith('..')||isAbsolute(rel))continue;await shared.track(path);
 }
 async function configuredModule(path,namespace=false){const module=await import(pathToFileURL(await shared.module(path)).href);if(module.components){const mapping=module.components({element:React.createElement});if(mapping&&typeof mapping.then==='function')throw new Error('Async component factories are unsupported: '+path);return mapping;}return namespace?module:module.default??module;}
 for(const [specifier,path] of Object.entries(request.options.imports??{}))mappedImports[specifier]=await configuredModule(path,true);
 if(request.options.components){
  components=await configuredModule(request.options.components);
  if(!components || typeof components!=='object' || typeof components.then==='function')throw new Error('Component mapping must synchronously return an object');
  components=Object.fromEntries(Object.entries(components).map(([name,adapter])=>{
   if(typeof adapter!=='function')throw new Error('Component adapter must be a function: '+name);
   return [name,props=>{try{const value=adapter(props);if(value&&typeof value.then==='function')throw new Error('Async component adapters are unsupported: '+name);return value;}catch(error){throw Object.assign(new Error(error.message,{cause:error}),{component:name,adapterPath:request.options.components});}}];
  }));
 }
 async function plugins(entries){const list=[];for(const entry of entries??[]){const plugin=await configuredModule(entry.path);if(typeof plugin!=='function')throw new Error('Plugin must export a function: '+entry.path);list.push([plugin,entry.options]);}return list;}
 const remarkPlugins=await plugins(request.options.remarkPlugins),rehypePlugins=await plugins(request.options.rehypePlugins);
 if(request.options.cache!==undefined&&request.options.cache!==false&&request.options.cache!=='content')throw new Error('cache must be false or content');
 const runtimeHash=request.options.cache==='content'?await cache.runtimeDigest():null;
 const results=[];
 for(const document of request.documents){
  let stage='compile',active=document,lineOffset=0;const start=performance.now();const inputs=new Inputs();inputs.inherit(shared);
  if(request.options.discovery==='compiler'&&document.path)await inputs.track(document.path);
  const allowed=new Set();
  const visiting=new Set(),modules=new Map();let compileMs=0,evaluateMs=0;const sourceMaps=[];
  try{
   for(const dependency of document.dependencies)allowed.add(await inputs.track(dependency.path));
   const fingerprintInputs=new Inputs();if(runtimeHash)for(const path of [...shared.list(),...document.dependencies.map(x=>x.path)])await fingerprintInputs.track(path);
   const key=runtimeHash?await cache.cacheKey(document,request.options,fingerprintInputs.list(),runtimeHash):null;
   const hit=key?await cache.get(key):null;
   if(hit){for(const path of hit.dependencies)await inputs.track(path);results.push({id:document.id,ok:true,html:hit.html,dependencies:inputs.list(),timing:{compileMs:0,evaluateMs:0,renderMs:0,totalMs:performance.now()-start},cacheHit:true});continue;}
   async function moduleFor(current){
    active=current;let key=resolve(projectRoot,current.path??document.id);if(current.path)try{key=await realpath(key);}catch(error){if(error.code!=='ENOENT')throw error;}
    if(visiting.size>32||modules.size>=256)throw new Error('Rendering document graph limit exceeded');
    if(visiting.has(key))throw new Error('Cyclic MDX document import: '+current.path);
    if(modules.has(key))return modules.get(key);
    visiting.add(key);const imports={};let childWorkMs=0;const prepared=body(current);lineOffset=prepared.lineOffset;
    function resolveImports(){return async tree=>{
     walk(tree,statement=>{if(statement.type==='ImportExpression')throw new Error('Dynamic imports are unsupported in MDX');});
     for(const node of tree.children){
      if(node.data?.estree)walk(node.data.estree,statement=>{if(statement.type==='ImportExpression')throw new Error('Dynamic imports are unsupported in MDX');});
      if(node.type!=='mdxjsEsm')continue;
      const rewritten=[];
      for(const statement of node.data.estree.body){
       function importError(message){const point=statement.loc?.start;throw Object.assign(new Error(message),{line:point?.line,column:point?point.column+1:undefined});}
       if(statement.source&&statement.type!=='ImportDeclaration')importError('Document re-exports are unsupported');
       if(statement.type!=='ImportDeclaration'){rewritten.push(statement);continue;}
       const spec=statement.source.value;
       if(Object.hasOwn(mappedImports,spec)){imports[spec]=mappedImports[spec];const replacement=importBinding(statement);if(replacement)rewritten.push(replacement);continue;}
       if(!current.path||!spec.startsWith('.')||!['.md','.mdx'].includes(extname(spec)))importError('Only registered relative MD/MDX imports are supported: '+spec);
       const path=resolve(dirname(key),spec);
       if(request.options.discovery!=='compiler'&&!allowed.has(path))importError('Import was not registered by mdx.input: '+spec);
       const childStarted=performance.now();
       const full=await inputs.track(path);const child={source:await inputs.read(full),path:full};
       const imported=await moduleFor(child);childWorkMs+=performance.now()-childStarted;active=current;lineOffset=prepared.lineOffset;
       // Child document components inherit the same explicit mapping.
       imports[spec]={...imported,default:props=>React.createElement(imported.default,{...props,components})};
       const replacement=importBinding(statement);if(replacement)rewritten.push(replacement);
      }
      node.data.estree.body=rewritten;
     }
    };}
    const t=performance.now();stage='compile';
    const compiled=await compile({value:prepared.value,path:current.path??document.id},{format:current.path?.endsWith('.md')?'md':'mdx',outputFormat:'function-body',SourceMapGenerator,remarkPlugins:[remarkGfm,...remarkPlugins,resolveImports],rehypePlugins:[[rehypeSlug,{prefix:'mdx-'}],...rehypePlugins]});
    compileMs+=performance.now()-t-childWorkMs;stage='evaluate';const evaluated=performance.now();const sourceURL='nift-mdx-'+sourceMaps.length;sourceMaps.push({sourceURL,map:compiled.map,document:current,lineOffset:prepared.lineOffset});const module=await run(String(compiled)+'\n//# sourceURL='+sourceURL,{...runtime,imports});evaluateMs+=performance.now()-evaluated;
    visiting.delete(key);modules.set(key,module);return module;
   }
   const module=await moduleFor(document);active=document;lineOffset=body(document).lineOffset;stage='render';const renderStart=performance.now();
   const html=renderToStaticMarkup(React.createElement(module.default,{components}));
   const result={id:document.id,ok:true,html,dependencies:inputs.list(),references:inputs.refs(),observations:[...shared.observations,...inputs.observations].map(([path,sha256])=>({path,sha256})),timing:{compileMs,evaluateMs,renderMs:performance.now()-renderStart,totalMs:performance.now()-start},cacheHit:false};if(key)await cache.put(key,result);results.push(result);
  }catch(error){
   let location=originalLocation(active,lineOffset,error);
   if(location.line===null && error.stack){
    for(const frame of error.stack.split('\n')){
     const match=/nift-mdx-(\d+):(\d+):(\d+)/.exec(frame);if(!match)continue;
     const record=sourceMaps[Number(match[1])];if(!record?.map)continue;
     const consumer=await new SourceMapConsumer(record.map);
     // AsyncFunction contributes two wrapper lines; columns in stack frames are one-based.
     const generatedLine=Number(match[2])-2,generatedColumn=Number(match[3])-1;
     let point=consumer.originalPositionFor({line:generatedLine,column:generatedColumn});
     if(point.line===null){let nearest;consumer.eachMapping(mapping=>{if(mapping.generatedLine===generatedLine&&mapping.originalLine!==null&&(!nearest||Math.abs(mapping.generatedColumn-generatedColumn)<Math.abs(nearest.generatedColumn-generatedColumn)))nearest=mapping;});if(nearest)point={line:nearest.originalLine,column:nearest.originalColumn};}
     consumer.destroy();
     if(point.line===null)continue;
     active=record.document;location=originalLocation(active,record.lineOffset,{line:point.line,column:point.column+1});break;
    }
   }
   results.push({id:document.id,ok:false,diagnostics:[diagnostic(stage,'mdx_'+stage+'_failed',error.message,active.path,location.line,location.column,error.component??/Expected component `([^`]+)`/.exec(error.message)?.[1]??null,error.adapterPath??null)]});}
 }
 return results;
}
