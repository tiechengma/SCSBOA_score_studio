import {ZipReader,BlobReader,ZipWriter,BlobWriter,Uint8ArrayReader,configure} from '@zip.js/zip.js';
import {validate,assetPattern,type Row} from './model.ts';
import {ImportBudget} from './import-budget.ts';
configure({useWebWorkers:false});
export const MAX_SOURCE=100*1024*1024,MAX_PACKAGE=512*1024*1024;
export async function digest(blob:Blob){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await blob.arrayBuffer())),b=>b.toString(16).padStart(2,'0')).join('');}
export async function verifyOriginals(rows:Iterable<Row>,staged:Map<string,Blob>,load:(key:string)=>Promise<Blob|undefined>){
 const verified=new Set<string>(),needed=new Map<string,Blob>();
 for(const row of rows)for(const source of row.sources){
  if(verified.has(source.asset))continue;
  const blob=staged.get(source.asset)??await load(source.asset);
  if(!blob||blob.size>MAX_SOURCE||await digest(blob)!==source.asset.split('.')[0])throw Error('Missing or damaged original: '+source.name);
  verified.add(source.asset);if(staged.has(source.asset))needed.set(source.asset,blob);
 }
 return needed;
}
export async function stage(file:File){if(file.size>MAX_SOURCE)throw Error('Source exceeds 100 MB.');const ext=file.name.split('.').pop()!.toLowerCase(),hash=await digest(file),key=`${hash}.${ext}`;if(!assetPattern.test(key))throw Error('Unsupported source format.');return {source:{asset:key,name:file.name,page:1,sha256:hash},blob:file};}
export async function readPackage(file:Blob,budget=new ImportBudget()){
 if(file.size>MAX_PACKAGE)throw Error('Package exceeds 512 MB.');
 const zip=new ZipReader(new BlobReader(file));try{
 const entries=await zip.getEntries();if(entries.length>10000||new Set(entries.map(e=>e.filename)).size!==entries.length||entries.reduce((n,e)=>n+e.uncompressedSize,0)>MAX_PACKAGE)throw Error('Oversized package or duplicate ZIP entries.');
 const files=new Map(entries.map(e=>[e.filename,e]));const manifest=files.get('manifest.json');if(!manifest||manifest.directory||manifest.uncompressedSize>20*1024*1024)throw Error('Missing or oversized manifest.');
 let totalExpanded=0;
 async function bounded(name:string,limit:number){
  const entry=files.get(name);if(!entry||entry.directory||entry.encrypted||entry.uncompressedSize>limit)throw Error('Invalid or missing attachment: '+name);
  const chunks:Uint8Array[]=[];let length=0,limitError:unknown;
  const stream=new WritableStream<Uint8Array>({write(chunk){
   try{length+=chunk.length;totalExpanded+=chunk.length;if(totalExpanded>MAX_PACKAGE)throw Error('Expanded package exceeds 512 MB.');if(length>limit)throw Error('Expanded attachment exceeds limits.');if(name==='manifest.json')budget.consumeMetadata(chunk.length);else budget.consumeBytes(chunk.length);chunks.push(chunk.slice());}
   catch(error){limitError=error;throw error;}
  }});
  try{await entry.getData!(stream,{checkSignature:true});}catch(error){throw limitError??error;}
  return new Blob(chunks as BlobPart[]);
 }
 const m=JSON.parse(await(await bounded('manifest.json',20*1024*1024)).text());if(m?.format!=='scsboa-score-studio'||![1,2].includes(m.version)||!Array.isArray(m.records)||m.records.length>50000)throw Error('Unsupported package.');budget.addRows(m.records.length);
 const assets=new Map<string,Blob>();for(const row of m.records){validate(row);row.awards??={};for(const s of row.sources){if(assets.has(s.asset))continue;budget.addAsset(s.asset);const blob=await bounded('assets/'+s.asset,MAX_SOURCE);if(await digest(blob)!==s.asset.split('.')[0])throw Error('Original attachment checksum mismatch.');assets.set(s.asset,blob);}}
 return {rows:m.records as Row[],assets};
 }finally{await zip.close();}
}
export async function exportPackage(rows:Row[],load:(key:string)=>Promise<Blob|undefined>){
 rows.forEach(validate);if(rows.length>50000)throw Error('Export at most 50,000 records.');const manifest=new TextEncoder().encode(JSON.stringify({format:'scsboa-score-studio',version:2,created:new Date().toISOString(),records:rows}));if(manifest.length>20*1024*1024)throw Error('Manifest exceeds 20 MB.');
 const assets=new Map<string,Blob>();let size=manifest.length;for(const r of rows)for(const s of r.sources){if(assets.has(s.asset))continue;const blob=await load(s.asset);if(!blob||blob.size>MAX_SOURCE||await digest(blob)!==s.asset.split('.')[0])throw Error('Missing or damaged original: '+s.name);assets.set(s.asset,blob);size+=blob.size;if(size>MAX_PACKAGE||assets.size>9999)throw Error('Export too large. Export one season at a time.');}
 const zip=new ZipWriter(new BlobWriter('application/zip'));await zip.add('manifest.json',new Uint8ArrayReader(manifest));for(const [key,blob] of assets)await zip.add('assets/'+key,new BlobReader(blob));return zip.close();
}
export function download(blob:Blob,name:string){const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),60000);}
