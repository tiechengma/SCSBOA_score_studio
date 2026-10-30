const runs=(indices:number[])=>{const groups:number[][]=[];for(const i of indices){if(!groups.length||i-groups.at(-1)!.at(-1)!>2)groups.push([i]);else groups.at(-1)!.push(i)}return groups.map(g=>Math.floor(g.reduce((a,b)=>a+b,0)/g.length));};
type Grid={xs:number[];ys:number[];clippedBottom?:boolean};
export function detectGrid(w:number,h:number,data:Uint8ClampedArray):Grid[]{const gray=(x:number,y:number)=>{const i=(y*w+x)*4;return .299*data[i]+.587*data[i+1]+.114*data[i+2]};const candidates:number[]=[],starts:Record<number,number>={};for(let y=0;y<h;y++){let start=-1,total=0,left=w;for(let x=0;x<=w;x++){if(x<w&&gray(x,y)<175){if(start<0)start=x}else if(start>=0){if(x-start>=Math.max(80,Math.floor(w/3))){total+=x-start;left=Math.min(left,start)}start=-1}}if(total>w*.4){candidates.push(y);starts[y]=left}}
 const blocks:number[][]=[];for(const y of runs(candidates)){if(!blocks.length||y-blocks.at(-1)!.at(-1)!>Math.max(80,h*.055))blocks.push([y]);else blocks.at(-1)!.push(y)}const result:Grid[]=[];
 for(const block of blocks){const left=Math.min(...block.map(y=>starts[y]??w)),ys=block.filter(y=>(starts[y]??w)<=left+5);if(ys.length<2)continue;const top=ys[0],bottom=ys.at(-1)!,vertical:number[]=[];for(let x=left+6;x<w;x++){let count=0;for(let y=top;y<=bottom;y++)if(gray(x,y)<95)count++;if(count>(bottom-top)*.7)vertical.push(x)}const xs=runs(vertical);if(xs.length>=18){
 // A phone screenshot can end after the score text but before the final row border.
 // Recover only near-full rows with continuing column rules; never infer hidden scores.
 const gaps=ys.slice(1).map((y,i)=>y-ys[i]).sort((a,b)=>a-b),rowHeight=gaps[Math.floor(gaps.length/2)],remaining=h-1-bottom;
 let clippedBottom=false;
 if(remaining>=rowHeight*.85&&remaining<=rowHeight*1.15){let continuing=0;for(const x of xs){let dark=0;for(let y=bottom+2;y<h;y++)if(gray(x,y)<95)dark++;if(dark>remaining*.7)continuing++;}if(continuing>=xs.length*.9){ys.push(h-1);clippedBottom=true;}}
 result.push({xs:[left,...xs],ys,clippedBottom});}}return result;
}
