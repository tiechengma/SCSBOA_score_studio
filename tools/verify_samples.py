"""Optional integration test against the user's local reference screenshots."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scorestudio.recognition import Recognizer,load_image
from scorestudio.model import COLUMNS

folder=Path(sys.argv[1])
# Transcribed from the provided reference tables, in printed column order.
expected={
'Screenshot 2026-10-26 212653.png':[
('Arroyo Knights Band & Colorguard',[8.1,8,16.1,7.8,7.9,15.7,31.8,7.4,7,14.4,8.2,8,16.2,30.6,8,7.8,15.8,78.2,0,0,78.2,83,82,165,82.5,80,81,161,80.5]),
('Wilson HS',[7.9,7.8,15.7,7.4,7.3,14.7,30.4,7.2,7.1,14.3,6.6,6.4,13,27.3,7.2,6.8,14,71.7,0,0,71.7,62,58,120,60,76,75,151,75.5]),
('San Luis Obispo High School Band',[7.3,7.2,14.5,7,6.9,13.9,28.4,7,6.7,13.7,6.3,5.9,12.2,25.9,6.8,6.5,13.3,67.6,0,0,67.6,57,52,109,54.5,60,59,119,59.5])],
'Screenshot 2026-10-26 212647.png':[
('Esperanza HS Entertainment Unit',[7.4,7.3,14.7,7.5,7.4,14.9,29.6,6.7,6.4,13.1,7.4,7.1,14.5,27.6,7.6,7.1,14.7,71.9,0,0,71.9,74,70,144,72,63,65,128,64]),
('Shadow Hills HS Regiment of the Realm',[7.3,7.2,14.5,7.7,7.6,15.3,29.8,6.9,6.6,13.5,7,6.6,13.6,27.1,7,6.4,13.4,70.3,0,0,70.3,69,67,136,68,66,68,134,67]),
('Camarillo High School Marching Band',[6.8,6.7,13.5,7.9,7.8,15.7,29.2,7.3,6.8,14.1,6.8,6,12.8,26.9,7.2,6.9,14.1,70.2,0,0,70.2,64,62,126,63,79,78,157,78.5]),
('Huntington Park High School Marching Band',[6.6,6.5,13.1,7.2,7.1,14.3,27.4,5.8,5.7,11.5,7.6,7.3,14.9,26.4,7.8,7.3,15.1,68.9,0,0,68.9,72,71,143,71.5,67,69,136,68]),
('Lakeside High School Lancer Regiment',[6.7,6.6,13.3,7.6,7.5,15.1,28.4,7.1,6.9,14,5.9,5.3,11.2,25.2,5.9,5.4,11.3,64.9,0,0,64.9,59,60,119,59.5,69,72,141,70.5]),
('Katella HS Knights Royal Regiment',[6.2,6.1,12.3,6.5,6.7,13.2,25.5,6.8,6.5,13.3,6.7,6.3,13,26.3,6.3,6,12.3,64.1,0,0,64.1,66,63,129,64.5,70,70,140,70]),
('Glendora HS Tartan Marching Band & Pageantry',[5.8,5.7,11.5,6.6,6.5,13.1,24.6,5.7,5.9,11.6,6.4,6.2,12.6,24.2,6,5.5,11.5,60.3,0,0,60.3,63,65,128,64,62,60,122,61])]
}
engine=Recognizer();report=[];all_rows=[]
for filename,truth in expected.items():
 rows,notes,ctx=engine.parse(load_image(folder/filename),{'name':filename,'asset':'test','page':1},lambda s:print(s,flush=True))
 assert len(rows)==len(truth),(filename,len(rows))
 for row,(school,scores) in zip(rows,truth):
  assert row['event']=='Loara FT' and row['date']=='2026-10-24'
  for (key,label),score in zip(COLUMNS,scores):
   if row['scores'].get(key)!=score:report.append((school,key,score,row['scores'].get(key)))
  if row['school']!=school:report.append((school,'school',school,row['school']))
 all_rows.extend(rows)
Path('tmp/final-sample-records.json').write_text(json.dumps(all_rows,indent=2),encoding='utf8')
print('290 score cells compared; mismatches:',json.dumps(report),flush=True)
assert not report,report
