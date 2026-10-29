import test from 'node:test';
import assert from 'node:assert/strict';
import 'fake-indexeddb/auto';
import {ZipWriter,BlobWriter,TextReader,BlobReader} from '@zip.js/zip.js';
import {blank,COLUMNS,warnings,schoolKey,schoolOptions} from '../src/model.ts';
import {selectExportRows} from '../src/export-selection.ts';
import {ImportBudget} from '../src/import-budget.ts';
import {readPackage,digest,verifyOriginals} from '../src/packages.ts';
import {checkedImageDimensions} from '../src/image-header.ts';
import {Cancellation} from '../src/cancellation.ts';
import * as db from '../src/db.ts';
const row=()=>({...blank(),school:'Wilson HS',event:'Test FT',date:'2026-10-24',division:'5AA',scores:{total:70}});
const limits={bytes:100000,metadata:10000,rows:10,assets:10};

async function fixture(text='fixture'){
 const blob=new Blob([text]),asset=(await digest(blob))+'.png';
 const r={...row(),sources:[{asset,name:'fixture.png',page:1}]};
 const manifest=JSON.stringify({format:'scsboa-score-studio',version:2,records:[r]});
 const zip=new ZipWriter(new BlobWriter());await zip.add('manifest.json',new TextReader(manifest));await zip.add('assets/'+asset,new BlobReader(blob));
 return {zip:await zip.close(),expanded:new TextEncoder().encode(manifest).length+blob.size};
}
test('multiple packages share actual expanded-byte, metadata, row and asset budgets',async()=>{
 const first=await fixture(),second=await fixture('other fixture');
 const bytes=new ImportBudget({...limits,bytes:first.expanded+second.expanded-1});
 await readPackage(first.zip,bytes);await assert.rejects(readPackage(second.zip,bytes),/expanded data/);
 const rows=new ImportBudget({...limits,rows:1});await readPackage(first.zip,rows);await assert.rejects(readPackage(second.zip,rows),/50,000/);
 const assets=new ImportBudget({...limits,assets:1});await readPackage(first.zip,assets);await assert.rejects(readPackage(second.zip,assets),/original files/);
 const metadata=new ImportBudget({...limits,metadata:1});await assert.rejects(readPackage(first.zip,metadata),/metadata/);
});
test('existing drafts consume the same budget before another package can be read',async()=>{
 const budget=new ImportBudget({...limits,rows:1}).seed([row()],new Map());
 await assert.rejects(readPackage((await fixture()).zip,budget),/50,000/);
 assert.throws(()=>new ImportBudget({...limits,bytes:100}).seed([row()],new Map()),/expanded data/);
});
test('untrusted image previews reject huge or malformed headers before decoding',async()=>{
 const bytes=new Uint8Array(24),v=new DataView(bytes.buffer);v.setUint32(0,0x89504e47);v.setUint32(4,0x0d0a1a0a);v.setUint32(12,0x49484452);v.setUint32(16,90000);v.setUint32(20,90000);
 await assert.rejects(checkedImageDimensions(new Blob([bytes]),'png'),/safe dimensions/);
 await assert.rejects(checkedImageDimensions(new Blob(['invalid image']),'png'),/Invalid PNG/);
 v.setUint32(16,8000);v.setUint32(20,5000);assert.deepEqual(await checkedImageDimensions(new Blob([bytes]),'png'),[8000,5000]);
});
test('case and whitespace variants share analytics/export keys without rewriting records',()=>{
 const records=[row(),{...row(),school:' wilson   hs ',date:'2026-10-25'}],before=JSON.stringify(records);
 assert.equal(schoolKey(records[0].school),schoolKey(records[1].school));assert.deepEqual(schoolOptions(records.map(r=>r.school)),['Wilson HS']);
 assert.equal(selectExportRows(records,'',['WILSON HS'],[]).length,2);assert.equal(JSON.stringify(records),before);
});
test('caption totals and negative scores are warned without changing source values',()=>{
 const scores=Object.fromEntries(COLUMNS.map(([k])=>[k,0]));Object.assign(scores,{'auxiliary.comp':83,'auxiliary.ach':82,'auxiliary.raw':999,'percussion.comp':80,'percussion.ach':81,'percussion.raw':999,'music.j1.stt':-1,'music.j1.mus':1});
 const before=JSON.stringify(scores),issues=warnings({...row(),scores});
 assert(issues.includes('Check sum: auxiliary.raw'));assert(issues.includes('Check sum: percussion.raw'));assert(issues.includes('Negative score: music.j1.stt'));assert.equal(JSON.stringify(scores),before);
 assert(!warnings({...row(),scores:{'penalties.total':-1}}).some(s=>s.startsWith('Negative score')));
});
test('cancellation rejects pending phases immediately and invokes task cleanup once',async()=>{
 const cancel=new Cancellation();let loading=0,rendering=0;
 cancel.onCancel(()=>loading++);cancel.onCancel(()=>rendering++);
 const pending=cancel.wait(new Promise<void>(()=>{}));cancel.cancel();cancel.cancel();
 await assert.rejects(pending,/cancelled/);assert.equal(loading,1);assert.equal(rendering,1);
 await assert.rejects(cancel.wait(Promise.resolve('late result')),/cancelled/);
});
test('no-op imports preserve revision/history, stale undo cannot erase newer changes, history keeps 50',async()=>{
 const first=await db.read();assert.equal(await db.commit([row()],new Map(),first.revision,'Initial'),true);
 const before=await db.read(),target=await db.undoTarget();assert(target);
 const same={...row(),scores:{total:70}};
 assert.equal(await db.commit([same],new Map(),before.revision,'Duplicate'),false);
 assert.equal((await db.read()).revision,before.revision);assert.deepEqual(await db.undoTarget(),target);
 await db.commit([{...row(),scores:{total:71}}],new Map(),before.revision,'Other tab');
 await assert.rejects(db.undo(target),/changed in another tab/);assert.equal((await db.read()).records[0].scores.total,71);
 assert.equal(await db.undo((await db.undoTarget())!),true);assert.equal((await db.read()).records[0].scores.total,70);
 const asset='preserved-test-asset',original=new Blob(['original retained']);
 for(let i=0;i<55;i++){const snap=await db.read();await db.commit([{...row(),scores:{total:100+i}}],i===0?new Map([[asset,original]]):new Map(),snap.revision,'Change '+i);}
 let count=0;while(await db.undoTarget()){await db.undo((await db.undoTarget())!);count++;}
 assert.equal(count,50);assert.equal((await db.read()).records[0].scores.total,104);assert.equal(await(await db.asset(asset))!.text(),'original retained');
});

test('shared originals are loaded once and only staged originals are scheduled for writing',async()=>{
 const blob=new Blob(['shared original']),asset=(await digest(blob))+'.pdf',r={...row(),sources:[{asset,name:'original.pdf',page:1},{asset,name:'original.pdf',page:2}]};let loads=0;
 const needed=await verifyOriginals([r,{...r,school:'Other HS'}],new Map(),async()=>{loads++;return blob;});assert.equal(loads,1);assert.equal(needed.size,0);
 const staged=await verifyOriginals([r],new Map([[asset,blob]]),async()=>{throw Error('Must not read stored copy');});assert.equal(staged.get(asset),blob);
});
