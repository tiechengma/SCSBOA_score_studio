/// <reference lib="webworker" />
import * as ort from 'onnxruntime-web/wasm';
import {detectGrid} from './ocr-grid.ts';
import {headerDate} from './ocr-header.ts';
import {blank,type Source} from './model.ts';
import {FIELD_COLUMNS,PARADE_LAYOUTS,paradeLayout,type ParadeLayout} from './columns.ts';
let session:ort.InferenceSession,chars:string[];
const canvas=(w:number,h:number)=>new OffscreenCanvas(Math.max(1,Math.round(w)),Math.max(1,Math.round(h)));
async function recognize(original:OffscreenCanvas,rect:number[],trim=true,binary=false){
 const [x,y,w,h]=rect;if(w<2||h<2)return {text:'',confidence:0};let c=canvas(w,h),ctx=c.getContext('2d',{willReadFrequently:true})!;ctx.drawImage(original,x,y,w,h,0,0,c.width,c.height);const pixelsImage=ctx.getImageData(0,0,c.width,c.height),data=pixelsImage.data;if(binary){for(let i=0;i<data.length;i+=4){const value=(data[i]+data[i+1]+data[i+2])/3<135?0:255;data[i]=data[i+1]=data[i+2]=value;}ctx.putImageData(pixelsImage,0,0);}let left=0,right=c.width-1,top=0,bottom=c.height-1;const dark=(x:number,y:number)=>{const i=(y*c.width+x)*4;return .299*data[i]+.587*data[i+1]+.114*data[i+2]<135};
 if(trim)for(let pass=0;pass<3;pass++){const col=(x:number)=>{let n=0;for(let y=top;y<=bottom;y++)n+=+dark(x,y);return n/(bottom-top+1)},row=(y:number)=>{let n=0;for(let x=left;x<=right;x++)n+=+dark(x,y);return n/(right-left+1)};if(col(left)>.85)left++;if(col(right)>.85)right--;if(row(top)>.85)top++;if(row(bottom)>.85)bottom--;}
 let x0=right,y0=bottom,x1=left,y1=top,found=false;for(let y=top;y<=bottom;y++)for(let x=left;x<=right;x++)if(dark(x,y)){found=true;x0=Math.min(x0,x);x1=Math.max(x1,x);y0=Math.min(y0,y);y1=Math.max(y1,y)}if(!found)return {text:'',confidence:1};const cw=x1-x0+1,ch=y1-y0+1,scale=Math.max(1,42/ch);let padded=canvas(Math.round(cw*scale)+10,Math.round(ch*scale)+10),p=padded.getContext('2d')!;p.fillStyle='white';p.fillRect(0,0,padded.width,padded.height);p.imageSmoothingQuality='high';p.drawImage(c,x0,y0,cw,ch,5,5,padded.width-10,padded.height-10);const width=Math.max(320,Math.ceil(48*padded.width/padded.height)),rw=Math.ceil(48*padded.width/padded.height);if(width>4096)return {text:'',confidence:0};let resized=canvas(rw,48),r=resized.getContext('2d')!;r.drawImage(padded,0,0,rw,48);const pixels=r.getImageData(0,0,rw,48).data,tensor=new Float32Array(3*48*width);for(let ch=0;ch<3;ch++)for(let y=0;y<48;y++)for(let x=0;x<rw;x++)tensor[ch*48*width+y*width+x]=pixels[(y*rw+x)*4+ch]/127.5-1;
 const feed=new ort.Tensor('float32',tensor,[1,3,48,width]),outputs=await session.run({[session.inputNames[0]]:feed}),out=outputs[session.outputNames[0]],values=out.data as Float32Array,v=out.dims[2];let text='',last=-1,sum=0,count=0;for(let t=0;t<out.dims[1];t++){let best=0;for(let k=1;k<v;k++)if(values[t*v+k]>values[t*v+best])best=k;if(best!==0&&best!==last){text+=chars[best];sum+=values[t*v+best];count++}last=best}feed.dispose();Object.values(outputs).forEach(o=>o.dispose());return {text:text.trim(),confidence:count?sum/count:0};
}
async function headings(c:OffscreenCanvas,end:number,start=0,xRatio=.35,wRatio=.28){const x=Math.floor(c.width*xRatio),w=Math.max(1,Math.floor(c.width*wRatio)),ctx=c.getContext('2d')!,height=Math.max(1,end-start),data=ctx.getImageData(x,start,w,height).data;const ys:number[]=[];for(let y=0;y<height;y++){let count=0;for(let xx=0;xx<w;xx++){const i=(y*w+xx)*4;if(data[i]+data[i+1]+data[i+2]<400)count++;}if(count>=2&&count<w*.8)ys.push(y)}const bands:number[][]=[];for(const y of ys){if(!bands.length||y-bands.at(-1)!.at(-1)!>3)bands.push([y]);else bands.at(-1)!.push(y)}const lines:string[]=[];for(const b of bands){if(b.length<3)continue;const {text}=await recognize(c,[x,start+b[0]-1,w,b.at(-1)!-b[0]+3],false);if(text)lines.push(text)}return lines;}

type Context={event:string;date:string;division:string;category?:string;scheme?:string;parade_layout?:ParadeLayout};
self.onmessage=async(event:MessageEvent<{bitmap:ImageBitmap;source:Source;base:string;context:Context&{pdfWords?:{text:string;y:number}[]}}>)=>{
 try{
  const {bitmap,source,base}=event.data;
  if(!session){ort.env.wasm.numThreads=1;ort.env.wasm.wasmPaths=base+'ocr/';chars=await(await fetch(base+'ocr/characters.json')).json();session=await ort.InferenceSession.create(base+'ocr/recognition.onnx',{executionProviders:['wasm']});}
  const c=canvas(bitmap.width,bitmap.height);c.getContext('2d')!.drawImage(bitmap,0,0);bitmap.close();
  const tables=detectGrid(c.width,c.height,c.getContext('2d')!.getImageData(0,0,c.width,c.height).data),rows=[],issues:string[]=[];
  const pdfWords=event.data.context.pdfWords??[];
  let context:Context={...event.data.context},previousBottom=0;
  for(const table of tables){
   const {xs,ys,headerTop}=table,top=ys[0];
   if(table.clippedBottom)issues.push('Bottom row reaches the screenshot edge. Visible scores were read; verify the last school and ranks against the original.');
   // Event titles live above the grid, while Parade division labels live to its left.
   const headerEnd=Math.max(previousBottom,headerTop);
   const lines=await headings(c,headerEnd,previousBottom);
   if(!lines.some(line=>headerDate(line))){const alternate=await headings(c,headerEnd,previousBottom,.25,.3);lines.push(...alternate.filter(line=>!lines.includes(line)));}
   const textBands=new Map<number,string[]>();
   for(const word of pdfWords){if(word.y<previousBottom||word.y>=headerEnd)continue;const key=Math.round(word.y/4);if(!textBands.has(key))textBands.set(key,[]);textBands.get(key)!.push(word.text);}
   lines.push(...[...textBands.values()].map(parts=>parts.join(' ')));
   let division='',eventName='',category='';
   for(const line of lines){
    if(/^(?:[1-6]A{1,2}|EXHIBITION)$/i.test(line.replace(/\s/g,'')))division=line.trim().toUpperCase();
    const date=headerDate(line);if(date)context.date=date;
    if(/\bFT\b|\bBR\b|Parade|Tournament|Field Show|Championship/i.test(line)&&line.length>eventName.length)eventName=line;
    if(/^(?:High|Middle|Junior High|Elementary)\s+School$/i.test(line.trim()))category=line.trim();
   }
   if(eventName)context.event=eventName;
   const height=Math.max(12,Math.round((ys[1]-ys[0])*.56)),labels:string[]=[];
   for(let j=1;j<Math.min(4,xs.length-1);j++)labels.push((await recognize(c,[xs[j]+2,top-height,xs[j+1]-xs[j]-4,height-2])).text);
   const parade=/Parade|\bBR\b/i.test(eventName||context.event)||(!eventName&&/^scsboa-parade/.test(context.scheme??''))||labels[0]?.toLowerCase()==='snd';
   let keys=FIELD_COLUMNS.map(([k])=>k),layout:ParadeLayout|undefined,tableNotes='';
   const judges:Record<string,string>={};
   if(parade){
    const leftLines=await headings(c,top,Math.max(previousBottom,headerTop-12),xs[0]/c.width,(xs[1]-xs[0])/c.width);
    lines.push(...leftLines);
    const found=leftLines.find(line=>/^(?:[1-6]A{1,2}|Round\s*\d+|DIV\s*\d+|EXHIBITION)$/i.test(line.trim()));
    if(found)division=found.trim().replace(/\s+/g,' ');
    for(let j=4;j<xs.length-1;j++)labels.push((await recognize(c,[xs[j]+2,top-height,xs[j+1]-xs[j]-4,height-2])).text);
    layout=paradeLayout(labels);
    if(!layout){issues.push(`${source.name}: Unsupported or cropped Parade column headers. No scores were assigned to guessed columns. Use a complete, clearer recap or add a record manually.`);previousBottom=ys.at(-1)!;continue;}
    keys=PARADE_LAYOUTS[layout];
    const sectionTitles:Record<string,string>={guard:'Color Guard',composition:'Composition','drum-major':'Drum Major',drill:'Drill Team'};
    let verified=true;
    for(const [section,expected] of Object.entries(sectionTitles)){
     const first=keys.indexOf(`parade.${section}.comp`);if(first<0)continue;
     const title=(await recognize(c,[xs[first+1]+2,headerTop+2,xs[first+4]-xs[first+1]-4,height-3])).text;
     lines.push(title);
     if(title.toLowerCase().replace(/[^a-z]/g,'')!==expected.toLowerCase().replace(/[^a-z]/g,''))verified=false;
    }
    if(!verified){issues.push(`${source.name}: Parade caption titles could not be verified. No scores were assigned to guessed captions. Use a complete, clearer recap or add a record manually.`);previousBottom=ys.at(-1)!;continue;}
    if(layout==='single-drum-major'){
     const end=keys.indexOf('parade.combined.total')+2;
     const internal=(await recognize(c,[xs[1]+2,headerTop+2,xs[end]-xs[1]-4,height-3])).text;
     if(internal){lines.push(internal);if(/Parade|\bBR\b/i.test(internal)&&!internal.toLowerCase().includes(context.event.toLowerCase()))tableNotes='Check OCR: the internal table heading differs from the event title; the title above the table was retained. ';}
    }
    const judgeGroups=new Map<string,number[]>();
    keys.forEach((key,i)=>{let group='';if(key.startsWith('parade.music.j1.'))group='parade.music.j1';else if(key.startsWith('parade.music.j2.'))group='parade.music.j2';else if(key.startsWith('parade.')&&!['parade.music.total','parade.combined.total'].includes(key))group=key.split('.').slice(0,2).join('.');else if(key==='penalties.raw')group='penalties';if(group){const indices=judgeGroups.get(group)??[];indices.push(i);judgeGroups.set(group,indices);}});
    for(const [group,indices] of judgeGroups){const first=indices[0],last=indices.at(-1)!;const name=(await recognize(c,[xs[first+1]+2,top-height*2+1,xs[last+2]-xs[first+1]-4,height-3])).text;if(name&&name.length<=500)judges[group]=name;}
    context.parade_layout=layout;context.category=category||context.category||'';
    const innerLines=await headings(c,top,headerTop);
    lines.push(...innerLines);
    if(innerLines.some(line=>/Parade|\bBR\b/i.test(line)&&!line.toLowerCase().includes(context.event.toLowerCase())))tableNotes='Check OCR: the internal table heading differs from the event title; the title above the table was retained. ';
   }
   const season=context.date?.slice(0,4)||'2026';context.scheme=`scsboa-${parade?'parade':'field'}-${season}`;
   if(!parade){delete context.parade_layout;delete context.category;if(xs.length-2>FIELD_COLUMNS.length){issues.push('Unsupported column layout: scores were not assigned to Field columns.');continue;}}
   if(division)context.division=division;else issues.push('Division header missing: verify continuation and column mapping.');
   previousBottom=ys.at(-1)!;
   const count=Math.min(keys.length,xs.length-2),header=lines.join(' | ');
   if(count<keys.length)issues.push('Right edge cropped: unavailable fields remain missing.');
   for(let i=0;i<ys.length-1;i++){
    self.postMessage({type:'progress',text:`${source.name} · page ${source.page} · row ${i+1}`});
    const y1=ys[i],y2=ys[i+1],mid=Math.floor((y1+y2)/2);if(y2-y1<10)continue;
    const r=blank();Object.assign(r,{event:context.event,date:context.date,division:context.division,scheme:context.scheme});
    if(parade){r.parade_layout=layout;r.category=context.category??'';r.judges={...judges};}
    r.season=season;r.sources=[source];r.header_text=header;
    const school=await recognize(c,[xs[0]+1,y1+2,xs[1]-xs[0]-2,mid-y1-1]);r.school=school.text;r.original_school=r.school;
    const low:string[]=[];if(school.confidence<.9)low.push('school');
    for(let j=0;j<count;j++)for(const [kind,y,h] of [['scores',y1+2,mid-y1-1],['ranks',mid,y2-mid-1]] as const){
     const rect=[xs[j+1]+2,y,xs[j+2]-xs[j+1]-4,h];let value=await recognize(c,rect),token=value.text.replace(/\s/g,'');const key=keys[j];
     if(kind==='ranks'&&(token!==''||value.confidence<.95)&&!/^\d+$/.test(token)){
      const retry=await recognize(c,rect,true,true),retried=retry.text.replace(/\s/g,'');
      if(/^\d+$/.test(retried)&&+retried>=1&&+retried<=10000){value=retry;token=retried;low.push(`${key} rank (enhanced contrast)`);}
     }
     if(/^-?\d+(\.\d+)?$/.test(token)&&Math.abs(+token)<=10000&&(kind==='scores'||(+token>=1&&Number.isInteger(+token))))r[kind][key]=+token;
     else if(token)low.push(`${key} ${kind} (${token})`);
     if(token&&value.confidence<.9)low.push(`${key} ${kind}`);
    }
    r.notes='Verify all fields against the original. '+(parade?'Check OCR: verify judge names against the original. ':'')+tableNotes+(table.clippedBottom&&i===ys.length-2?'Check OCR: bottom row is cropped; verify all scores and ranks. ':'')+(count<keys.length?'Cropped right edge. ':'')+(low.length?'Check OCR: '+[...new Set(low)].join(', '):'');rows.push(r);
   }
  }
  if(previousBottom<c.height-10){const tail=await headings(c,c.height,previousBottom);if(tail.some(line=>/^(?:[1-6]A{1,2}|EXHIBITION)$/i.test(line.replace(/\s/g,''))))issues.push('Partial table at page edge: verify the split row and division on the next page.');}
  if(!rows.length)issues.push('No complete supported grid found. Add a record manually or use a clearer screenshot.');
  self.postMessage({type:'result',rows,issues,context});
 }catch(error){self.postMessage({type:'error',message:String(error)});}
};
