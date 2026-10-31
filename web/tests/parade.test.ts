import test from 'node:test';
import assert from 'node:assert/strict';
import {blank,validate,identity,eventKey,merge,warnings} from '../src/model.ts';
import {PARADE_LAYOUTS,columnsFor,paradeLayout} from '../src/columns.ts';
import {exportPackage,readPackage,digest} from '../src/packages.ts';
import {selectExportRows} from '../src/export-selection.ts';
import {ZipReader,BlobReader,TextWriter} from '@zip.js/zip.js';
const parade=()=>({...blank(),scheme:'scsboa-parade-2026',parade_layout:'double-composition' as const,category:'High School',school:'Arroyo HS',event:'Example',date:'2026-10-24',division:'6A',scores:{total:93.75}});
test('Parade and Field cannot collide in saved identity or same-event export',()=>{
 const p=parade(),f={...blank(),school:p.school,event:p.event,date:p.date,division:p.division};
 assert.notEqual(identity(p),identity(f));assert.notEqual(eventKey(p),eventKey(f));
 assert.notEqual(identity(p),identity({...p,category:'Middle School'}));
 assert.equal(identity(p),identity({...p,category:' high  school '}));
 assert.deepEqual(selectExportRows([p,f],'',[],[eventKey(p)]),[p]);
});
test('Parade layout uses column headers and exact width, never count alone',()=>{
 const headers=(n:number,prefix:string[])=>[...prefix,...Array(n-prefix.length).fill('Tot')];
 assert.equal(paradeLayout(headers(27,['Snd','Tun','Tech'])),'double-composition');
 assert.equal(paradeLayout(headers(31,['Snd','Tun','Tech'])),'double-composition-drill');
 assert.equal(paradeLayout(headers(28,['Snd','Tech','MuCa'])),'single-drum-major');
 assert.equal(paradeLayout(headers(27,['Snd','Tech','MuCa'])),undefined);
 assert.equal(paradeLayout(headers(27,['STT','MUS','Tot'])),undefined);
 assert.equal(paradeLayout(headers(30,['Snd','Tun','Tech'])),undefined);
});
test('Parade keeps optional absent captions absent and validates the scoring layout',()=>{
 const p=parade();p.scores=Object.fromEntries(PARADE_LAYOUTS[p.parade_layout].map(k=>[k,0])) as typeof p.scores;validate(p);
 assert.equal(warnings(p).filter(s=>s.includes('missing')).length,0);
 assert(!columnsFor(p).some(([k])=>k.startsWith('parade.drill.')));
 assert.throws(()=>validate({...p,parade_layout:undefined}));
 assert.throws(()=>validate({...p,parade_layout:['double-composition']}));
 assert.throws(()=>validate({...p,scores:{'music.total':50}}));
 assert.throws(()=>validate({...p,scores:{'parade.drill.total':50}}));
 assert.throws(()=>validate({...p,category:{name:'High School'}}));
});
test('layout changes require a whole-record merge decision',()=>{
 const p=parade(),r=merge(p,{...p,parade_layout:'double-composition-drill',scores:{total:94,'parade.drill.total':85}});
 assert.equal(r.conflicts[0].category,'record');assert.notEqual(r.conflicts[0].saved,r.conflicts[0].incoming);assert.deepEqual(r.row,p);
});
test('Parade package v3 roundtrips source bytes and metadata; Field export remains v2',async()=>{
 const blob=new Blob(['parade source']),hash=await digest(blob),p={...parade(),sources:[{asset:hash+'.png',sha256:hash,name:'source.png',page:1}]};
 const packed=await exportPackage([p],async()=>blob),decoded=await readPackage(packed);assert.deepEqual(decoded.rows,[p]);assert.equal(await decoded.assets.get(hash+'.png')!.text(),'parade source');
 const version=async(b:Blob)=>{const reader=new ZipReader(new BlobReader(b));try{return JSON.parse(await (await reader.getEntries()).find(e=>e.filename==='manifest.json')!.getData!(new TextWriter())).version;}finally{await reader.close();}};
 assert.equal(await version(packed),3);assert.equal(await version(await exportPackage([{...blank(),school:'A',event:'B',date:'2026-10-24',division:'1A'}],async()=>undefined)),2);
});
test('Parade arithmetic warnings preserve printed data including negative penalties',()=>{
 const p={...parade(),scores:{subtotal:91.8,'penalties.raw':-3,total:88.8,'parade.guard.comp':84,'parade.guard.ach':83,'parade.guard.raw':168}};
 const before=structuredClone(p);assert(!warnings(p).includes('Check penalty and final total'));assert(warnings(p).includes('Check sum: parade.guard.raw'));assert.deepEqual(p,before);
});
