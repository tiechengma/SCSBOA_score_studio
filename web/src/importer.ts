import * as pdfjs from 'pdfjs-dist';
import pdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import {checkedImageDimensions,assertImageDimensions} from './image-header.ts';
import {stage,MAX_SOURCE} from './packages.ts';
import {ImportBudget} from './import-budget.ts';
import {Cancellation} from './cancellation.ts';
import type {Row,Source} from './model.ts';
pdfjs.GlobalWorkerOptions.workerSrc=pdfWorker;

async function openPDF(blob:Blob,cancel:Cancellation){
 const data=await cancel.wait(blob.arrayBuffer());cancel.check();
 const task=pdfjs.getDocument({data,maxImageSize:40000000});
 let destroyed:Promise<void>|undefined;
 const destroy=()=>destroyed??=task.destroy();
 const off=cancel.onCancel(()=>{void destroy().catch(()=>{});});
 try{return {pdf:await cancel.wait(task.promise),close:async()=>{off();await destroy();}};}
 catch(error){off();await destroy().catch(()=>{});throw error;}
}
async function renderPage(p:pdfjs.PDFPageProxy,c:HTMLCanvasElement,v:pdfjs.PageViewport,cancel:Cancellation){
 cancel.check();const task=p.render({canvasContext:c.getContext('2d')!,canvas:c,viewport:v});
 const off=cancel.onCancel(()=>task.cancel());
 try{await cancel.wait(task.promise);}finally{off();}
}
async function bitmap(source:ImageBitmapSource,cancel:Cancellation){
 return cancel.wait(createImageBitmap(source).then(value=>{if(cancel.cancelled){value.close();throw cancel.error();}return value;}));
}
export async function renderOriginalPDF(blob:Blob,page:number,target:HTMLElement,cancel=new Cancellation()){
 let opened:Awaited<ReturnType<typeof openPDF>>|undefined,c:HTMLCanvasElement|undefined;
 try{
  if(blob.size>MAX_SOURCE)throw Error('Original exceeds 100 MB.');
  opened=await openPDF(blob,cancel);if(page>opened.pdf.numPages)throw Error('Original page is unavailable.');
  const p=await cancel.wait(opened.pdf.getPage(page)),v=p.getViewport({scale:1.5});
  assertImageDimensions(Math.ceil(v.width),Math.ceil(v.height));if(v.width*v.height>20000000)throw Error('Original preview is too large. Download the original instead.');
  c=document.createElement('canvas');c.width=Math.ceil(v.width);c.height=Math.ceil(v.height);c.className='source-image';c.setAttribute('aria-label','Original PDF page '+page);
  await renderPage(p,c,v,cancel);cancel.check();if(target.isConnected)target.replaceChildren(c);p.cleanup();
 }catch(error){if(!cancel.cancelled&&target.isConnected)target.textContent=String(error);}
 finally{if(c&&!c.isConnected)c.width=c.height=1;await opened?.close();}
}

export function importImages(files:File[],progress:(s:string)=>void,budget=new ImportBudget()){
 const cancel=new Cancellation();let worker:Worker|undefined;
 const promise=(async()=>{
  if(files.length>100||files.reduce((n,f)=>n+f.size,0)>512*1024*1024)throw Error('Import at most 100 files / 512 MB per batch.');
  const rows:Row[]=[],issues:string[]=[],assets=new Map<string,Blob>();let pixels=0;
  const check=(w:number,h:number)=>{assertImageDimensions(w,h);if((pixels+=w*h)>400000000)throw Error('Image/page batch exceeds safe pixel limits. Resize or split this batch.');};
  const collect=(out:{rows:Row[];issues:string[]})=>{budget.addRecognizedRows(out.rows);for(const row of out.rows)rows.push(row);for(const issue of out.issues)issues.push(issue);};
  const recognize=(image:ImageBitmap,source:Source,context:unknown)=>{
   if(cancel.cancelled){image.close();throw cancel.error();}
   const pending=new Promise<any>((resolve,reject)=>{
    worker??=new Worker(new URL('./ocr.worker.ts',import.meta.url),{type:'module'});
    worker.onerror=e=>reject(Error(e.message));
    worker.onmessage=e=>{if(e.data.type==='progress')progress(e.data.text);else if(e.data.type==='error')reject(Error(e.data.message));else if(e.data.type==='result')resolve(e.data);};
    worker.postMessage({bitmap:image,source,context,base:new URL(import.meta.env.BASE_URL,location.href).href},[image]);
   });return cancel.wait(pending);
  };
  const off=cancel.onCancel(()=>worker?.terminate());
  try{
   for(const file of files){
    cancel.check();if(file.size>MAX_SOURCE)throw Error('Source exceeds 100 MB.');
    const ext=file.name.split('.').pop()!.toLowerCase();if(!['pdf','png','jpg','jpeg','webp'].includes(ext))throw Error('Use PNG, JPEG, WebP or PDF. Convert HEIC/HEIF before importing.');
    budget.consumeBytes(file.size);progress('Preparing '+file.name);
    const staged=await cancel.wait(stage(file));budget.addAsset(staged.source.asset);assets.set(staged.source.asset,file);
    let context={event:'',date:'',division:''};
    if(ext==='pdf'){
     const opened=await openPDF(file,cancel);
     try{
      if(opened.pdf.numPages>100)throw Error('PDF exceeds 100 pages.');
      for(let page=1;page<=opened.pdf.numPages;page++){
       cancel.check();progress(`${file.name} · rendering page ${page} of ${opened.pdf.numPages}`);
       const p=await cancel.wait(opened.pdf.getPage(page)),v=p.getViewport({scale:3});check(Math.ceil(v.width),Math.ceil(v.height));
       const c=document.createElement('canvas');c.width=Math.ceil(v.width);c.height=Math.ceil(v.height);
       try{
        await renderPage(p,c,v,cancel);
        const text=await cancel.wait(p.getTextContent());const words=text.items.filter((item):item is import('pdfjs-dist/types/src/display/api').TextItem=>'str' in item).map(item=>({text:item.str,y:pdfjs.Util.transform(v.transform,item.transform)[5]}));
        const out=await recognize(await bitmap(c,cancel),{...staged.source,page},{...context,pdfWords:words});collect(out);context=out.context;
       }finally{p.cleanup();c.width=c.height=1;}
      }
      if(opened.pdf.numPages>1)issues.push('Multi-page PDF: check split rows, inherited headings and missing schools against every page.');
     }finally{await opened.close();}
    }else{
     const [width,height]=await cancel.wait(checkedImageDimensions(file,ext));check(width,height);
     const image=await bitmap(file,cancel);
     try{assertImageDimensions(image.width,image.height);collect(await recognize(image,staged.source,context));}finally{image.close();}
    }
   }
   cancel.check();return {rows,issues:[...new Set(issues)],assets};
  }finally{off();worker?.terminate();}
 })();return {promise,cancel:()=>cancel.cancel()};
}
