import fs from 'node:fs';
import {PARADE_LAYOUTS} from '../src/columns.ts';
import {validate,warnings} from '../src/model.ts';
const samples=JSON.parse(fs.readFileSync(new URL('../tests/fixtures/parade-2026.json',import.meta.url),'utf8'));
const report=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),errors=[];let scores=0,ranks=0,records=0;
for(const sample of samples)for(const [school,values,rank,rankValues] of sample.rows){
 records++;const row=report.rows.find(r=>r.event===sample.event&&r.school===school);
 if(!row){errors.push(`Missing ${sample.event}: ${school}`);continue;}
 try{validate(row)}catch(e){errors.push(`${school}: ${e.message}`)}
 for(const [key,value] of Object.entries({date:sample.date,division:sample.division,parade_layout:sample.layout,category:'High School',scheme:'scsboa-parade-2026'}))if(row[key]!==value)errors.push(`${school} ${key}: ${row[key]} != ${value}`);
 const keys=PARADE_LAYOUTS[sample.layout];if(values.length!==keys.length)throw Error('Incorrect reference column count: '+sample.event);
 values.forEach((v,i)=>{scores++;if(row.scores[keys[i]]!==v)errors.push(`${sample.event} / ${school} / ${keys[i]}: ${row.scores[keys[i]]} != ${v}`)});
 rankValues.forEach((v,i)=>{ranks++;if((row.ranks[keys[i]]??null)!==v)errors.push(`${sample.event} / ${school} / rank ${keys[i]}: ${row.ranks[keys[i]]??null} != ${v}`)});
 if(row.ranks.total!==rank)errors.push(`${school}: final rank ${row.ranks.total} != ${rank}`);
 console.log(school,JSON.stringify({judges:row.judges,warnings:warnings(row)}));
}
console.log(JSON.stringify({records,scores,ranks,recognized:report.rows.length,errors},null,2));
if(errors.length)process.exitCode=1;
