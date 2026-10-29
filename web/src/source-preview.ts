import type {Row,Source} from './model.ts';
import {checkedImageDimensions,assertImageDimensions} from './image-header.ts';
import {renderOriginalPDF} from './importer.ts';
import {Cancellation} from './cancellation.ts';
import {download} from './packages.ts';

/** Load just one source at a time; a package hash does not establish safe image dimensions. */
export function sourcePreview(dialog:HTMLDialogElement,row:Row,target:HTMLElement,load:(key:string)=>Promise<Blob|undefined>,full=false){
 if(!row.sources.length){target.textContent='No original attached (manual record).';return;}
 const list=document.createElement('div'),view=document.createElement('div');
 view.className=full?'original-scroll':'original-preview';target.append(list,view);
 let current:Cancellation|undefined,pending=Promise.resolve();
 const clear=()=>{view.querySelectorAll('canvas').forEach(c=>{c.width=c.height=1;});view.replaceChildren();};
 dialog.addEventListener('close',()=>{current?.cancel();clear();},{once:true});
 const preview=(source:Source)=>{
  current?.cancel();const cancel=new Cancellation();current=cancel;
  pending=pending.then(async()=>{
   if(cancel.cancelled||!dialog.isConnected)return;clear();view.textContent='Checking and loading original…';
   try{
    const blob=await load(source.asset);cancel.check();if(!blob)throw Error('Missing original: '+source.name);
    const ext=source.asset.split('.').pop()!;
    if(ext==='pdf'){await renderOriginalPDF(blob,source.page,view,cancel);return;}
    if(!['png','jpg','jpeg','webp'].includes(ext))throw Error('Preview is not supported for this format. Download the original instead.');
    await checkedImageDimensions(blob,ext);cancel.check();
    // Wait for decoding to settle before starting another preview, even after cancellation.
    const image=await createImageBitmap(blob);
    try{
     cancel.check();assertImageDimensions(image.width,image.height);
     const scale=Math.min(1,4096/image.width,4096/image.height,Math.sqrt(8000000/(image.width*image.height)));
     const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.floor(image.width*scale));canvas.height=Math.max(1,Math.floor(image.height*scale));
     canvas.className=full?'original-full':'source-image';canvas.setAttribute('role','img');canvas.setAttribute('aria-label',source.name);
     canvas.getContext('2d')!.drawImage(image,0,0,canvas.width,canvas.height);
     if(dialog.isConnected&&!cancel.cancelled)view.replaceChildren(canvas);else canvas.width=canvas.height=1;
    }finally{image.close();}
   }catch(error){if(!cancel.cancelled&&dialog.isConnected)view.textContent=String(error);}
  });
 };
 for(const source of row.sources){
  const item=document.createElement('div');item.className='source-actions';
  const title=document.createElement('p');title.textContent=source.name+' · page '+source.page;
  const show=document.createElement('button');show.type='button';show.className='secondary';show.textContent='Preview original';show.onclick=()=>preview(source);
  const save=document.createElement('button');save.type='button';save.className='secondary';save.textContent='Download original';
  save.onclick=async()=>{save.disabled=true;try{const blob=await load(source.asset);if(!blob)throw Error('Original is missing.');download(blob,source.name);}catch(error){title.textContent=source.name+' — '+String(error);}finally{save.disabled=false;}};
  item.append(title,show,save);list.append(item);
 }
 preview(row.sources[0]);
}
