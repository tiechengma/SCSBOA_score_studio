import {schoolKey,type Row} from './model.ts';
export function selectExportRows(rows:Row[],season:string,schools:string[],events:string[]){
 const schoolSet=new Set(schools.map(schoolKey)),eventSet=new Set(events);
 return rows.filter(r=>(!season||r.season===season)&&(!schoolSet.size||schoolSet.has(schoolKey(r.school)))&&(!eventSet.size||eventSet.has(JSON.stringify([r.date,r.event]))));
}
