import test from 'node:test';
import assert from 'node:assert/strict';
import {detectGrid} from '../src/ocr-grid.ts';

function fixture(height:number,extend:boolean){
  const width=1200,data=new Uint8ClampedArray(width*height*4).fill(255);
  const black=(x:number,y:number)=>{const i=(y*width+x)*4;data[i]=data[i+1]=data[i+2]=0;};
  for(const y of [100,140,180])for(let x=20;x<=1100;x++)black(x,y);
  for(let x=50;x<=1100;x+=35)for(let y=100;y<(extend?height:181);y++)black(x,y);
  return detectGrid(width,height,data);
}
test('near-full screenshot-edge row is recovered and explicitly marked cropped',()=>{
  const tables=fixture(219,true);
  assert.equal(tables.length,1);
  assert.deepEqual(tables[0].ys,[100,140,180,218]);
  assert.equal(tables[0].clippedBottom,true);
});
test('blank footer and heavily cropped rows are not invented as complete rows',()=>{
  assert.deepEqual(fixture(219,false)[0].ys,[100,140,180]);
  assert.deepEqual(fixture(201,true)[0].ys,[100,140,180]);
  assert.equal(fixture(219,false)[0].clippedBottom,false);
});
