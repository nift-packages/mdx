import {load} from './dependencies.mjs';
import {diagnostic} from './protocol.mjs';
import {performance} from 'node:perf_hooks';
const {compile,run}=await load('@mdx-js/mdx');
const runtime=await load('react/jsx-runtime');
const React=(await load('react')).default;
const {renderToStaticMarkup}=await load('react-dom/server');
const remarkGfm=(await load('remark-gfm')).default;
const rehypeSlug=(await load('rehype-slug')).default;
function importPolicy(){return tree=>{for(const node of tree.children)if(node.type==='mdxjsEsm')for(const statement of node.data.estree.body)if(statement.type==='ImportDeclaration' || statement.source)throw new Error('Module resolution is not yet supported; imports must not execute implicitly');};}
export async function renderBatch(request){
 const results=[];
 for(const document of request.documents){
  let stage='compile';const start=performance.now();
  try{
   const compiled=await compile({value:document.source,path:document.path??document.id},{outputFormat:'function-body',remarkPlugins:[remarkGfm,importPolicy],rehypePlugins:[[rehypeSlug,{prefix:'mdx-'}]]});
   const compiledAt=performance.now();stage='evaluate';const module=await run(String(compiled),runtime);const evaluatedAt=performance.now();stage='render';
   const html=renderToStaticMarkup(React.createElement(module.default));
   results.push({id:document.id,ok:true,html,dependencies:[],timing:{compileMs:compiledAt-start,evaluateMs:evaluatedAt-compiledAt,renderMs:performance.now()-evaluatedAt,totalMs:performance.now()-start}});
  }catch(error){results.push({id:document.id,ok:false,diagnostics:[diagnostic(stage,'mdx_'+stage+'_failed',error.message,document.path,error.line??null,error.column??null)]});}
 }
 return results;
}
