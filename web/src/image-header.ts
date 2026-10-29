export function assertImageDimensions(width:number,height:number){
 if(!Number.isSafeInteger(width)||!Number.isSafeInteger(height)||width<1||height<1||width>20000||height>20000||width*height>40000000)throw Error('Original image exceeds safe dimensions (40 megapixels / 20,000 pixels per side). Download the original instead.');
}
export async function checkedImageDimensions(blob:Blob,ext:string){
 if(blob.size>100*1024*1024)throw Error('Original exceeds 100 MB.');
 const size=await imageDimensions(blob,ext);assertImageDimensions(...size);return size;
}
// Read dimensions before allocating a decoded bitmap. JPEG headers are scanned with bounded reads.
export async function imageDimensions(file:Blob,ext:string):Promise<[number,number]>{
 const bytes=new Uint8Array(await file.slice(0,32).arrayBuffer()),v=new DataView(bytes.buffer);
 if(ext==='png'){if(bytes.length<24||v.getUint32(0)!==0x89504e47||v.getUint32(4)!==0x0d0a1a0a||v.getUint32(12)!==0x49484452)throw Error('Invalid PNG header.');return [v.getUint32(16),v.getUint32(20)];}
 if(ext==='webp'){if(bytes.length<25||new TextDecoder().decode(bytes.slice(0,4))!=='RIFF'||new TextDecoder().decode(bytes.slice(8,12))!=='WEBP')throw Error('Invalid WebP header.');const type=new TextDecoder().decode(bytes.slice(12,16));if(type==='VP8X'&&bytes.length>=30)return [1+bytes[24]+(bytes[25]<<8)+(bytes[26]<<16),1+bytes[27]+(bytes[28]<<8)+(bytes[29]<<16)];if(type==='VP8L'&&bytes[20]===0x2f){const n=v.getUint32(21,true);return [(n&0x3fff)+1,((n>>>14)&0x3fff)+1];}if(type==='VP8 '&&bytes.length>=30&&bytes[23]===0x9d&&bytes[24]===1&&bytes[25]===0x2a)return [v.getUint16(26,true)&0x3fff,v.getUint16(28,true)&0x3fff];throw Error('Unsupported WebP header.');}
 if(!['jpg','jpeg'].includes(ext)||bytes[0]!==255||bytes[1]!==216)throw Error('Invalid JPEG header.');let offset=2;for(let segments=0;segments<10000&&offset<file.size;segments++){const b=new Uint8Array(await file.slice(offset,offset+12).arrayBuffer());if(b.length<4||b[0]!==255)throw Error('Invalid JPEG segment.');if(b[1]===255){offset++;continue;}const marker=b[1];if(marker===0xd9||marker===0xda)break;if(marker===0x01||(marker>=0xd0&&marker<=0xd7)){offset+=2;continue;}const length=(b[2]<<8)+b[3];if(length<2)throw Error('Invalid JPEG length.');if([0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf].includes(marker)){if(b.length<9)throw Error('Truncated JPEG dimensions.');return [(b[7]<<8)+b[8],(b[5]<<8)+b[6]];}offset+=2+length;}throw Error('JPEG dimensions not found.');
}
