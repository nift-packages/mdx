// Investigation only. Trusted authored MDX executes JavaScript at build time.
import {compile, run} from '@mdx-js/mdx';
import * as runtime from 'react/jsx-runtime';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import remarkGfm from 'remark-gfm';
import rehypeSlug from 'rehype-slug';
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {resolve, dirname, extname} from 'node:path';
import {pathToFileURL, fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {performance} from 'node:perf_hooks';
const components = {Aside: ({type='note', children}) => React.createElement('aside', {'data-type':type}, children)};
const generated = resolve(dirname(fileURLToPath(import.meta.url)), '.generated');
await mkdir(generated, {recursive:true});
function body(source) { return source.replace(/^---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/, ''); }
export async function render(document) {
  if (!document.ok) throw new Error('Parser rejected document; rendering refused');
  const started = performance.now();
  const allowed = new Set((document.dependencies || []).map(d => resolve(d.path)));
  const visiting = new Set();
  let compileMs=0;
  async function build(source, path, imported=false) {
    const key = resolve(path || '__inline__.mdx');
    if (visiting.has(key)) throw new Error('Cyclic MDX import: '+key);
    visiting.add(key);
    function importsPlugin() { return async tree => {
      for (const node of tree.children) if (node.type === 'mdxjsEsm') {
        for (const statement of node.data.estree.body) if (statement.type === 'ImportDeclaration') {
          const spec = statement.source.value;
          if (!spec.startsWith('.') || !['.md','.mdx'].includes(extname(spec))) throw new Error('Prototype supports only relative MD/MDX imports: '+spec);
          if (!path) throw new Error('Inline document needs an explicit path to resolve imports');
          const child = resolve(dirname(key), spec);
          if (!allowed.has(child)) throw new Error('Import not registered by mdx.input: '+child);
          statement.source.value = await build(await readFile(child,'utf8'),child,true);
          delete statement.source.raw;
        }
      }
    }; }
    const t=performance.now();
    const compiled = await compile({value:body(source),path:key}, {outputFormat:imported?'program':'function-body',remarkPlugins:[remarkGfm,importsPlugin],rehypePlugins:[rehypeSlug]});
    compileMs += performance.now()-t; // inclusive child time: fixtures report root-only separately
    visiting.delete(key);
    if (imported) {
      const output=resolve(generated,createHash('sha256').update(String(compiled)).digest('hex')+'.mjs');
      await writeFile(output,String(compiled));
      return pathToFileURL(output).href;
    }
    return compiled;
  }
  const compiled=await build(document.source,document.path);
  const t=performance.now();
  const module=await run(String(compiled),{...runtime,baseUrl:pathToFileURL(resolve(document.path || '__inline__.mdx'))});
  const evaluated=performance.now();
  const html=renderToStaticMarkup(React.createElement(module.default,{components}));
  return {ok:true,html,timing:{compileMs,evaluateMs:evaluated-t,renderMs:performance.now()-evaluated,totalMs:performance.now()-started},maxRssKiB:process.resourceUsage().maxRSS};
}
if (process.argv[2]) {
  try {
    const request=JSON.parse(process.argv[2] === '--file' ? await readFile(process.argv[3],'utf8') : process.argv[2]);
    const results=[];
    for (const document of (Array.isArray(request)?request:[request])) results.push(await render(document));
    console.log(process.argv[3] === '--html' ? results[0].html : JSON.stringify(Array.isArray(request)?results:results[0]));
  } catch(error) { console.log(JSON.stringify({ok:false,stage:'compile-or-render',message:error.message,line:error.line,column:error.column})); process.exitCode=1; }
}
