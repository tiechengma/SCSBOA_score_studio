import {COLUMNS} from './columns.ts';
export {COLUMNS, MAIN} from './columns.ts';
export type Source={asset:string;name:string;page:number;sha256?:string};
export type Row={season:string;date:string;event:string;division:string;school:string;original_school:string;scheme:string;scores:Record<string,number|null>;ranks:Record<string,number|null>;judges:Record<string,string>;awards:Record<string,string>;sources:Source[];notes:string;header_text?:string};
export const DEFAULT='Arroyo Knight Band & Colorguard';
export const normalize=(s:string)=>s.trim().replace(/\s+/g,' ').toLowerCase();
export const schoolName=(s:string)=>['arroyo knight band & colorguard','arroyo knights band & colorguard'].includes(normalize(s))?DEFAULT:s.trim();
export const identity=(r:Row)=>JSON.stringify([r.season,r.date,r.event,r.division,schoolName(r.school)].map(normalize));
export const blank=():Row=>({season:'2026',date:'',event:'',division:'',school:'',original_school:'',scheme:'scsboa-field-2026',scores:{},ranks:{},judges:{},awards:{},sources:[],notes:''});
export const assetPattern=/^[a-f0-9]{64}\.(pdf|png|jpe?g|webp|bmp|tiff?|heic|heif)$/;
const obj=(v:unknown):v is Record<string,any>=>!!v&&typeof v==='object'&&!Array.isArray(v);
export function validate(r:unknown):asserts r is Row {
 if(!obj(r))throw Error('Record must be an object.');
 for(const key of ['season','date','event','division','school','scheme'])if(typeof r[key]!=='string'||!r[key].trim()||r[key].length>500)throw Error(`${key} is required (maximum 500 characters).`);
 if(!/^\d{4}$/.test(r.season)||!/^\d{4}-\d{2}-\d{2}$/.test(r.date)||!Number.isFinite(Date.parse(r.date))||new Date(r.date).toISOString().slice(0,10)!==r.date)throw Error('Enter a valid year and date.');
 const fields=new Set(COLUMNS.map(c=>c[0]));
 for(const category of ['scores','ranks']){if(!obj(r[category]))throw Error(`Invalid ${category}.`);for(const [key,v] of Object.entries(r[category])){if(!fields.has(key))throw Error('Unknown score field.');if(v!==null&&(typeof v!=='number'||!Number.isFinite(v)||Math.abs(v)>10000))throw Error(`${key}: expected a finite number, not text.`);if(category==='ranks'&&v!==null&&(!Number.isInteger(v)||(v as number)<1))throw Error('Ranks must be positive whole numbers.');}}
 if(!Array.isArray(r.sources)||r.sources.length>1000||!obj(r.judges))throw Error('Invalid sources or judges.');
 for(const s of r.sources)if(!obj(s)||typeof s.name!=='string'||s.name.length>500||!Number.isInteger(s.page)||s.page<1||s.page>100||typeof s.asset!=='string'||!assetPattern.test(s.asset)||(s.sha256!==undefined&&s.sha256!==s.asset.split('.')[0]))throw Error('Invalid original attachment reference.');
 for(const [k,v] of Object.entries(r.judges))if(['__proto__','constructor','prototype'].includes(k)||typeof v!=='string'||v.length>500)throw Error('Invalid judge.');
 for(const k of ['notes','original_school','header_text'])if(r[k]!==undefined&&(typeof r[k]!=='string'||r[k].length>30000))throw Error(`Invalid ${k}.`);
 validateAwards(r.awards??{});
}
export function validateAwards(awards:unknown):asserts awards is Record<string,string>{if(!obj(awards)||Object.keys(awards).length>100)throw Error('At most 100 awards are allowed.');const seen=new Set();for(const [k,v] of Object.entries(awards)){if(!k.trim()||k.length>200||['__proto__','constructor','prototype'].includes(k)||typeof v!=='string'||!v.trim()||v.length>2000||seen.has(normalize(k)))throw Error('Awards need unique names and source notes.');seen.add(normalize(k));}}
export type Conflict={category:'scores'|'ranks'|'judges'|'awards'|'record';field:string;saved:unknown;incoming:unknown};
export function merge(old:Row,next:Row):{row:Row;conflicts:Conflict[]}{
 const row=structuredClone(old),conflicts:Conflict[]=[];
 if(old.scheme!==next.scheme)return {row,conflicts:[{category:'record',field:'scheme',saved:old.scheme,incoming:next.scheme}]};
 for(const category of ['scores','ranks','judges','awards'] as const){const dest=row[category]??={};for(let [key,value] of Object.entries(next[category]??{})){if(value===null||value==='')continue;if(category==='awards')key=Object.keys(dest).find(k=>normalize(k)===normalize(key))??key;const prev=(dest as any)[key];if(prev==null||prev==='')Object.defineProperty(dest,key,{value,writable:true,enumerable:true,configurable:true});else if(prev!==value)conflicts.push({category,field:key,saved:prev,incoming:value});}}
 for(const source of next.sources)if(!row.sources.some(s=>s.asset===source.asset&&s.page===source.page&&s.name===source.name))row.sources.push(structuredClone(source));
 if(!row.notes)row.notes=next.notes;if(!row.original_school)row.original_school=next.original_school;
 return {row,conflicts};
}
export function warnings(r:Row){const out:string[]=[];if(/Check OCR|OCR normalized/.test(r.notes))out.push('OCR review needed');for(const k of ['event','date','division'] as const)if(!r[k])out.push(k+' required');const s=r.scores;const missing=COLUMNS.filter(([k])=>s[k]==null).length;if(missing)out.push(`${missing} missing score fields`);if(r.date&&r.date.slice(0,4)!==r.season)out.push('Date and season differ');for(const [total,parts] of [['music.j1.total',['music.j1.stt','music.j1.mus']],['music.j2.total',['music.j2.stt','music.j2.mus']],['music.total',['music.j1.total','music.j2.total']],['ge.j1.total',['ge.j1.comp','ge.j1.comm']],['ge.j2.total',['ge.j2.comp','ge.j2.comm']],['ge.total',['ge.j1.total','ge.j2.total']],['visual.total',['visual.comp','visual.exc']],['subtotal',['music.total','ge.total','visual.total']]] as [string,string[]][]){if(s[total]!=null&&parts.every(k=>s[k]!=null)&&Math.abs(s[total]!-parts.reduce((a,k)=>a+s[k]!,0))>.015)out.push(`Check sum: ${total}`);}if(s.total!=null&&s.subtotal!=null&&s['penalties.total']!=null&&Math.abs(s.subtotal-Math.abs(s['penalties.total'])-s.total)>.015)out.push('Check penalty and final total');return out;}
