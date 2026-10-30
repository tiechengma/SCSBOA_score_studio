const months=['January','February','March','April','May','June','July','August','September','October','November','December'];

export function headerDate(line:string):string {
  const match=line.replace(/\b0ctober\b/gi,'October').match(/\b(January|February|March|April|May|June|July|August|September|October|November|December)\W*(\d{1,2})\W*(20\d{2})\b/i);
  if(!match)return '';
  const month=months.findIndex(m=>m.toLowerCase()===match[1].toLowerCase())+1;
  const value=`${match[3]}-${String(month).padStart(2,'0')}-${match[2].padStart(2,'0')}`;
  const parsed=new Date(value+'T00:00:00Z');
  return Number.isFinite(+parsed)&&parsed.toISOString().slice(0,10)===value?value:'';
}
