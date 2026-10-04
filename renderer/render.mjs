import {diagnostic} from './protocol.mjs';
export async function renderBatch(request){return request.documents.map(document=>({id:document.id,ok:false,diagnostics:[diagnostic('compile','not_implemented','Compiler integration is checkpoint 04',document.path)]}));}
