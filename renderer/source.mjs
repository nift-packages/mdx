export function body(document){
 const {source}=document;let end=0;
 if(document.frontmatter?.present){
  end=document.frontmatter.end?.offset;
  if(!Number.isInteger(end)||end<0||end>Buffer.byteLength(source)||Buffer.from(source).subarray(0,end).toString('utf8')!==document.frontmatter.source)throw new Error('Invalid preserved frontmatter boundary');
 }else if(source.startsWith('---\n')||source.startsWith('---\r\n')||source.startsWith('---\r')){
  const match=/^---(?:\r\n|\r|\n)[\s\S]*?^---(?:(?:\r\n|\r|\n)|$)/m.exec(source);
  if(!match)throw new Error('Unclosed frontmatter');end=Buffer.byteLength(match[0]);
 }
 const prefix=Buffer.from(source).subarray(0,end).toString('utf8');
 return {value:Buffer.from(source).subarray(end).toString('utf8'),lineOffset:(prefix.match(/\r\n|\r|\n/g)||[]).length};
}
export function originalLocation(document,lineOffset,error){
 if(!Number.isInteger(error.line))return {line:null,column:null};
 const line=error.line+lineOffset;
 const text=document.source.split(/\r\n|\r|\n/)[line-1]??'';
 return {line,column:Number.isInteger(error.column)?Buffer.byteLength(text.slice(0,error.column-1))+1:null};
}
