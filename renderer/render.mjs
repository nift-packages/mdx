import {load} from './dependencies.mjs';
import {diagnostic} from './protocol.mjs';
import {Inputs} from './inputs.mjs';
import {pathToFileURL} from 'node:url';
import {body,originalLocation} from './source.mjs';
import {performance} from 'node:perf_hooks';
const {compile,run}=await load('@mdx-js/mdx');
const runtime=await load('react/jsx-runtime');
const React=(await load('react')).default;
const {renderToStaticMarkup}=await load('react-dom/server');
const remarkGfm=(await load('remark-gfm')).default;
const rehypeSlug=(await load('rehype-slug')).default;
function importPolicy(){return tree=>{for(const node of tree.children)if(node.type==='mdxjsEsm')for(const statement of node.data.estree.body)if(statement.type==='ImportDeclaration' || statement.source)throw new Error('Module resolution is not yet supported; imports must not execute implicitly');};}
export async function renderBatch(request){
 const inputs=new Inputs();let components={};
 if(request.options.components){
  const module=await import(pathToFileURL(await inputs.track(request.options.components)).href);
  components=module.components?module.components({element:React.createElement}):module.default;
  if(!components || typeof components!=='object' || typeof components.then==='function')throw new Error('Component mapping must synchronously return an object');
  components=Object.fromEntries(Object.entries(components).map(([name,adapter])=>{
   if(typeof adapter!=='function')throw new Error('Component adapter must be a function: '+name);
   return [name,props=>{const value=adapter(props);if(value&&typeof value.then==='function')throw new Error('Async component adapters are unsupported: '+name);return value;}];
  }));
 }
 const results=[];
 for(const document of request.documents){
  let stage='compile',lineOffset=0;const start=performance.now();
  try{
   const prepared=body(document);lineOffset=prepared.lineOffset;
   const compiled=await compile({value:prepared.value,path:document.path??document.id},{outputFormat:'function-body',remarkPlugins:[remarkGfm,importPolicy],rehypePlugins:[[rehypeSlug,{prefix:'mdx-'}]]});
   const compiledAt=performance.now();stage='evaluate';const module=await run(String(compiled),runtime);const evaluatedAt=performance.now();stage='render';
   const html=renderToStaticMarkup(React.createElement(module.default,{components}));
   results.push({id:document.id,ok:true,html,dependencies:inputs.list(),timing:{compileMs:compiledAt-start,evaluateMs:evaluatedAt-compiledAt,renderMs:performance.now()-evaluatedAt,totalMs:performance.now()-start}});
  }catch(error){const location=originalLocation(document,lineOffset,error);results.push({id:document.id,ok:false,diagnostics:[diagnostic(stage,'mdx_'+stage+'_failed',error.message,document.path,location.line,location.column)]});}
 }
 return results;
}
