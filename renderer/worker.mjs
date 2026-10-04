import {parentPort,workerData} from 'node:worker_threads';
import {VERSION,diagnostic} from './protocol.mjs';
try {
 const {renderBatch}=await import('./render.mjs');
 parentPort.postMessage({version:VERSION,ok:true,results:await renderBatch(workerData)});
} catch(error){parentPort.postMessage({version:VERSION,ok:false,diagnostics:[diagnostic('renderer', 'renderer_failed',error.message)]});}
