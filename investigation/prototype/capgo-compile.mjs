import {compile} from '@mdx-js/mdx';
import remarkGfm from 'remark-gfm';
import rehypeSlug from 'rehype-slug';
import {readFile} from 'node:fs/promises';
import {performance} from 'node:perf_hooks';
const rows=[];
for (const path of process.argv.slice(2)) {
 const source=await readFile(path,'utf8');const body=source.replace(/^---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/,'');const start=performance.now();
 try {const out=await compile({value:body,path},{remarkPlugins:[remarkGfm],rehypePlugins:[rehypeSlug]});rows.push({path,bytes:Buffer.byteLength(source),ok:true,compileMs:performance.now()-start,outputBytes:Buffer.byteLength(String(out)),peakRssKiB:process.resourceUsage().maxRSS});}
 catch(e){rows.push({path,bytes:Buffer.byteLength(source),ok:false,message:e.message,line:e.line,column:e.column});}
}
console.log(JSON.stringify(rows,null,2));
