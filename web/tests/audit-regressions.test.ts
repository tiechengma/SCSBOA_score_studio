import test from 'node:test';
import assert from 'node:assert/strict';
import {ZipReader} from '@zip.js/zip.js';
import {blank,validate,eventKey} from '../src/model.ts';
import {readPackage} from '../src/packages.ts';
import {sourceFilename} from '../src/source-filename.ts';
import {selectExportRows} from '../src/export-selection.ts';

const row=()=>({...blank(),date:'2026-10-28',school:'School',event:'Otay Ranch FT',division:'3A'});

test('download name cannot turn an original into an executable or HTML file',()=>{
  const source={asset:'a'.repeat(64)+'.png',name:'../../recap.html',page:1};
  assert.equal(sourceFilename(source),'recap.png');
  assert.equal(sourceFilename({...source,name:'C:\\files\\recap.exe'}),'recap.png');
  assert.equal(sourceFilename({...source,name:'recap\u202egnp.exe'}),'recap_gnp.png');
  assert.equal(sourceFilename({...source,name:'Screenshot 2026.png'}),'Screenshot 2026.png');
  assert.throws(()=>sourceFilename({...source,asset:'a'.repeat(64)+'.exe'}));
});

test('nested extension metadata and oversized judges are rejected before saving',()=>{
  let nested:unknown='payload';for(let i=0;i<30;i++)nested={next:nested};
  assert.throws(()=>validate({...row(),extension:nested}),/deeply nested/);
  assert.throws(()=>validate({...row(),judges:Object.fromEntries(Array.from({length:101},(_,i)=>['judge'+i,'Name']))}),/100 judge/);
  const malicious=JSON.parse(JSON.stringify(row()).replace(/}$/,',"__proto__":{"polluted":true}}'));
  assert.throws(()=>validate(malicious),/Unsafe metadata/);
  validate({...row(),extension:{sourceVersion:2,description:'retained metadata'}});
});

test('archive enumeration stops at the limit without materializing every entry',async t=>{
  let visited=0;
  t.mock.method(ZipReader.prototype,'getEntriesGenerator',async function*(){
    for(let i=0;i<20000;i++){visited++;yield {filename:'entry-'+i,uncompressedSize:0};}
  });
  await assert.rejects(readPackage(new Blob()),/Oversized package/);
  assert.equal(visited,10001);
});

test('same-event names use consistent identity in views and filtered export',()=>{
  const a=row(),b={...row(),school:'Second school',event:'  OTAY   RANCH ft '},c={...row(),date:'2026-10-29'};
  assert.equal(eventKey(a),eventKey(b));
  assert.notEqual(eventKey(a),eventKey(c));
  assert.deepEqual(selectExportRows([a,b,c],'',[],[eventKey(a)]),[a,b]);
  assert.deepEqual(selectExportRows([a,b,c],'',[],[JSON.stringify([a.date,a.event])]),[a,b]);
});
