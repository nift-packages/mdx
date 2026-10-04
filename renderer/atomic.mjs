import {rename} from 'node:fs/promises';
import {setTimeout as delay} from 'node:timers/promises';
// Windows can briefly lock the destination during concurrent replacement.
export async function replace(source,destination){
 for(let attempt=0;;attempt++){
  try{return await rename(source,destination);}
  catch(error){if(process.platform!=='win32'||!['EPERM','EACCES','EBUSY'].includes(error.code)||attempt>=5)throw error;await delay(20*2**attempt);}
 }
}
