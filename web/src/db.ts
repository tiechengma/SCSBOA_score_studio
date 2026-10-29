import {identity,validate,type Row} from './model.ts';
export type Snapshot={records:Row[];revision:number};
export const IS_QA=Boolean(import.meta.env?.DEV&&typeof location!=='undefined'&&new URL(location.href).searchParams.get('qa')==='1');
const open=new Promise<IDBDatabase>((resolve,reject)=>{const request=indexedDB.open(IS_QA?'scsboa-score-studio-isolated-qa':'scsboa-score-studio-web',1);request.onupgradeneeded=()=>{const db=request.result;db.createObjectStore('records');db.createObjectStore('assets');db.createObjectStore('settings');db.createObjectStore('history',{autoIncrement:true});};request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);request.onblocked=()=>reject(Error('Close other Score Studio tabs to update the library.'));});
const request=<T>(r:IDBRequest<T>)=>new Promise<T>((ok,no)=>{r.onsuccess=()=>ok(r.result);r.onerror=()=>no(r.error)});
const done=(t:IDBTransaction)=>new Promise<void>((ok,no)=>{t.oncomplete=()=>ok();t.onerror=()=>no(t.error);t.onabort=()=>no(t.error??Error('Library transaction cancelled.'))});
export async function read():Promise<Snapshot>{const db=await open,t=db.transaction(['records','settings'],'readonly');const [records,revision]=await Promise.all([request(t.objectStore('records').getAll()),request(t.objectStore('settings').get('revision'))]);return {records,revision:revision??0};}
export async function setting(key:string,value?:unknown){const db=await open,t=db.transaction('settings',value===undefined?'readonly':'readwrite'),s=t.objectStore('settings');if(value===undefined)return request(s.get(key));const complete=done(t);s.put(value,key);await complete;}
export async function asset(key:string):Promise<Blob|undefined>{return request((await open).transaction('assets').objectStore('assets').get(key));}
export const HISTORY_LIMIT=50;
function stable(value:unknown):unknown{
 if(Array.isArray(value))return value.map(stable);
 if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>[k,stable(v)]));
 return value;
}
export const sameRecord=(a:Row,b:Row)=>JSON.stringify(stable(a))===JSON.stringify(stable(b));
function sameRecords(a:Row[],b:Row[]){const previous=new Map(a.map(r=>[identity(r),r]));return a.length===b.length&&b.every(r=>{const old=previous.get(identity(r));return old!==undefined&&sameRecord(old,r);});}
async function stale(t:IDBTransaction,complete:Promise<void>):Promise<never>{t.abort();await complete.catch(()=>{});throw Error('The library changed in another tab. Refresh and confirm again.');}
export async function commit(rows:Row[],assets:Map<string,Blob>,expected:number,label:string){
 rows.forEach(validate);if(new Set(rows.map(identity)).size!==rows.length)throw Error('Duplicate record identities.');
 const db=await open,t=db.transaction(['records','assets','history','settings'],'readwrite'),complete=done(t);
 const settings=t.objectStore('settings'),rev=await request(settings.get('revision'));
 if((rev??0)!==expected)return stale(t,complete);
 const before:Row[]=await request(t.objectStore('records').getAll());
 if(sameRecords(before,rows)){assets.forEach((blob,key)=>t.objectStore('assets').put(blob,key));await complete;return false;}
 const history=t.objectStore('history');history.add({before,label,at:new Date().toISOString()});
 const keys=await request(history.getAllKeys());for(const key of keys.slice(0,Math.max(0,keys.length-HISTORY_LIMIT)))history.delete(key);
 const store=t.objectStore('records');store.clear();rows.forEach(r=>store.put(r,identity(r)));assets.forEach((blob,key)=>t.objectStore('assets').put(blob,key));settings.put(expected+1,'revision');await complete;return true;
}
export type UndoTarget={revision:number;id:IDBValidKey;label:string;at:string};
export async function undoTarget():Promise<UndoTarget|null>{
 const db=await open,t=db.transaction(['history','settings'],'readonly');
 const [cursor,rev]=await Promise.all([request(t.objectStore('history').openCursor(null,'prev')),request(t.objectStore('settings').get('revision'))]);
 return cursor?{revision:rev??0,id:cursor.primaryKey,label:cursor.value.label,at:cursor.value.at}:null;
}
export async function undo(target:UndoTarget){
 const db=await open,t=db.transaction(['records','history','settings'],'readwrite'),complete=done(t);
 const [cursor,rev]=await Promise.all([request(t.objectStore('history').openCursor(null,'prev')),request(t.objectStore('settings').get('revision'))]);
 if(!cursor||(rev??0)!==target.revision||indexedDB.cmp(cursor.primaryKey,target.id)!==0)return stale(t,complete);
 const store=t.objectStore('records');store.clear();cursor.value.before.forEach((r:Row)=>store.put(r,identity(r)));cursor.delete();t.objectStore('settings').put((rev??0)+1,'revision');await complete;return true;
}
