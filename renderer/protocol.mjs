export const VERSION=1;
export const LIMITS={requestBytes:16*1024*1024,sourceBytes:256*1024,aggregateBytes:8*1024*1024,documents:1000,responseBytes:64*1024*1024};
export function diagnostic(stage,code,message,path=null,line=null,column=null){return {stage,code,message,path,line,column};}
export function validate(request){
 if(!request || request.version!==VERSION || !Array.isArray(request.documents) || !request.documents.length || request.documents.length>LIMITS.documents)throw new Error('Invalid protocol version or document count');
 const ids=new Set();let total=0;
 for(const doc of request.documents){
  if(!doc || typeof doc.id!=='string' || !doc.id || doc.id.length>4096 || ids.has(doc.id) || typeof doc.source!=='string' || (doc.path!==null && typeof doc.path!=='string') || !Array.isArray(doc.dependencies))throw new Error('Invalid document or duplicate request ID');
  ids.add(doc.id);const bytes=Buffer.byteLength(doc.source);total+=bytes;if(bytes>LIMITS.sourceBytes || total>LIMITS.aggregateBytes)throw new Error('Source transport limit exceeded');
 }
 if(!request.options || request.options.policy!=='trusted')throw new Error('Rendering requires explicit policy: trusted');
 return request;
}
