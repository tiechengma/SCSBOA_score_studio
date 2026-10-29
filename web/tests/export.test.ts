import test from 'node:test';
import assert from 'node:assert/strict';
import {blank} from '../src/model.ts';
import {selectExportRows} from '../src/export-selection.ts';
const rows=[{...blank(),school:'Arroyo Knights Band & Colorguard',season:'2026',date:'2026-10-24',event:'Loara FT'},{...blank(),school:'Wilson HS',season:'2026',date:'2026-10-24',event:'Loara FT'},{...blank(),school:'Wilson HS',season:'2027',date:'2027-10-24',event:'Loara FT'}];
test('export filters intersect season, schools and dated events without changing records',()=>{
 const before=JSON.stringify(rows);
 assert.equal(selectExportRows(rows,'',[],[]).length,3);
 assert.equal(selectExportRows(rows,'2026',['Wilson HS'],[]).length,1);
 assert.equal(selectExportRows(rows,'',['Wilson HS'],[JSON.stringify(['2026-10-24','Loara FT'])]).length,1);
 assert.equal(selectExportRows(rows,'2027',[],[JSON.stringify(['2026-10-24','Loara FT'])]).length,0);
 assert.equal(JSON.stringify(rows),before);
});
test('export school aliases and multi-selection keep all matching records',()=>{
 assert.equal(selectExportRows(rows,'',['Arroyo Knight Band & Colorguard'],[]).length,1);
 assert.equal(selectExportRows(rows,'2026',['Arroyo Knight Band & Colorguard','Wilson HS'],[]).length,2);
});
