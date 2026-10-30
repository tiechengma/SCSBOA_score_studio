import test from 'node:test';
import assert from 'node:assert/strict';
import {headerDate} from '../src/ocr-header.ts';
import {blank,validate} from '../src/model.ts';

test('recap dates include phone screenshot and existing desktop formats',()=>{
  assert.equal(headerDate('Wednesday, October 28, 2026'),'2026-10-28');
  assert.equal(headerDate('Saturday, 0ctober 24, 2026'),'2026-10-24');
  assert.equal(headerDate('February 29, 2028'),'2028-02-29');
  for(const text of ['February 29, 2026','October 32, 2026','ber 28, 2026','Head Judge: Amy Mack'])assert.equal(headerDate(text),'');
});
test('missing competition date explains the recovery without a misleading length error',()=>{
  assert.throws(()=>validate({...blank(),school:'Sweetwater HS Red Devil Corps',event:'Otay Ranch FT',division:'2A'}),/Competition date is missing.*Open this record/);
});
