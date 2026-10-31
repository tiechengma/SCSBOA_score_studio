export const FIELD_COLUMNS: [string,string][] = [["music.j1.stt", "Music \u00b7 Judge 1 \u00b7 STT"], ["music.j1.mus", "Music \u00b7 Judge 1 \u00b7 MUS"], ["music.j1.total", "Music \u00b7 Judge 1 \u00b7 Total"], ["music.j2.stt", "Music \u00b7 Judge 2 \u00b7 STT"], ["music.j2.mus", "Music \u00b7 Judge 2 \u00b7 MUS"], ["music.j2.total", "Music \u00b7 Judge 2 \u00b7 Total"], ["music.total", "Music \u00b7 Total"], ["ge.j1.comp", "GE \u00b7 Judge 1 \u00b7 COMP EFF"], ["ge.j1.comm", "GE \u00b7 Judge 1 \u00b7 COMM EFF"], ["ge.j1.total", "GE \u00b7 Judge 1 \u00b7 Total"], ["ge.j2.comp", "GE \u00b7 Judge 2 \u00b7 COMP EFF"], ["ge.j2.comm", "GE \u00b7 Judge 2 \u00b7 COMM EFF"], ["ge.j2.total", "GE \u00b7 Judge 2 \u00b7 Total"], ["ge.total", "GE \u00b7 Total"], ["visual.comp", "Visual \u00b7 VIS COMP"], ["visual.exc", "Visual \u00b7 EXC"], ["visual.total", "Visual \u00b7 Total"], ["subtotal", "Subtotal"], ["penalties.raw", "Penalties \u00b7 PEN"], ["penalties.total", "Penalties \u00b7 Total"], ["total", "Final total"], ["auxiliary.comp", "Auxiliary \u00b7 COMP"], ["auxiliary.ach", "Auxiliary \u00b7 ACH"], ["auxiliary.raw", "Auxiliary \u00b7 Raw total"], ["auxiliary.total", "Auxiliary \u00b7 Factored total"], ["percussion.comp", "Percussion \u00b7 COMP"], ["percussion.ach", "Percussion \u00b7 ACH"], ["percussion.raw", "Percussion \u00b7 Raw total"], ["percussion.total", "Percussion \u00b7 Factored total"]];
export const FIELD_MAIN: string[] = ["total", "music.total", "ge.total", "visual.total", "auxiliary.total", "percussion.total"];

export type ParadeLayout='double-composition'|'double-composition-drill'|'single-drum-major';
const musicJudge=(j:number,fields:string[])=>[...fields.map(f=>`parade.music.j${j}.${f}`),`parade.music.j${j}.total`];
const show=['parade.showmanship.atun','parade.showmanship.dm','parade.showmanship.band','parade.showmanship.total'];
const march=['parade.marching.march','parade.marching.maneuver','parade.marching.total'];
const auxiliary=(name:string)=>['comp','ach','raw','total'].map(k=>`parade.${name}.${k}`);
const double=[...musicJudge(1,['sound','tuning','technique']),...musicJudge(2,['sound','tuning','technique']),'parade.music.total',...show,...march,'subtotal','penalties.raw','total',...auxiliary('guard'),...auxiliary('composition')];
export const PARADE_LAYOUTS:Record<ParadeLayout,string[]>={
 'double-composition':double,
 'double-composition-drill':[...double,...auxiliary('drill')],
 'single-drum-major':['parade.music.j1.sound','parade.music.j1.technique','parade.music.j1.musicality','parade.music.total',...show,...march,'parade.combined.total','subtotal','penalties.raw','penalties.total','total',...auxiliary('guard'),...auxiliary('drum-major'),...auxiliary('drill')]
};
const titles:Record<string,string>={combined:'Combined captions',music:'Music',showmanship:'Showmanship',marching:'Marching & Maneuvering',guard:'Color Guard',composition:'Composition',drill:'Drill Team','drum-major':'Drum Major',sound:'Sound',tuning:'Tuning',technique:'Technique',musicality:'MuCa',atun:'AtUn / AtU',dm:'DM',band:'Band',march:'Marching',maneuver:'Maneuvering / Man',comp:'Composition',ach:'Achievement',raw:'Raw total',total:'Total',j1:'Judge 1',j2:'Judge 2'};
const fieldLabels=new Map(FIELD_COLUMNS);
export const PARADE_COLUMNS:[string,string][]=[...new Set(Object.values(PARADE_LAYOUTS).flat())].map(k=>[k,fieldLabels.get(k)??k.split('.').slice(1).map(p=>titles[p]??p).join(' · ')]);
export const COLUMNS:[string,string][]=[...FIELD_COLUMNS,...PARADE_COLUMNS.filter(([k])=>!fieldLabels.has(k))];
export const PARADE_MAIN=['total','parade.combined.total','parade.music.total','parade.showmanship.total','parade.marching.total','parade.guard.total','parade.composition.total','parade.drum-major.total','parade.drill.total'];
export const MAIN=[...FIELD_MAIN,...PARADE_MAIN.filter(k=>!FIELD_MAIN.includes(k))];
export const isParade=(r:{scheme?:string})=>/^scsboa-parade(?:-|$)/.test(r.scheme??'');
export const scoringFamily=(r:{scheme?:string})=>isParade(r)?'Parade':'Field';
export function columnsFor(r:{scheme:string;parade_layout?:ParadeLayout;scores?:Record<string,number|null>}){
 if(!isParade(r))return FIELD_COLUMNS;
 const keys=r.parade_layout?PARADE_LAYOUTS[r.parade_layout]:PARADE_COLUMNS.map(([k])=>k);
 return PARADE_COLUMNS.filter(([k])=>keys.includes(k)||r.scores?.[k]!=null).sort((a,b)=>{const ai=keys.indexOf(a[0]),bi=keys.indexOf(b[0]);return (ai<0?999:ai)-(bi<0?999:bi)});
}
export function paradeLayout(labels:string[]):ParadeLayout|undefined{
 const words=labels.map(s=>s.toLowerCase().replace(/[^a-z]/g,''));
 if(words[0]!=='snd')return;
 if(words[1]==='tun'&&words[2]==='tech')return labels.length===27?'double-composition':labels.length===31?'double-composition-drill':undefined;
 if(words[1]==='tech'&&words[2]==='muca'&&labels.length===28)return 'single-drum-major';
}
