import type {Row} from './model.ts';

export const IMPORT_LIMITS={bytes:512*1024*1024,metadata:20*1024*1024,rows:50000,assets:9999};
/** One budget for the existing draft queue plus every file in the new batch. */
export class ImportBudget {
 private bytes=0;
 private metadata=0;
 private rows=0;
 private assets=new Set<string>();
 private limits:typeof IMPORT_LIMITS;
 constructor(limits={...IMPORT_LIMITS}){this.limits=limits;}
 consumeBytes(count:number){
  if(!Number.isSafeInteger(count)||count<0||this.bytes+count>this.limits.bytes)throw Error('Combined import exceeds 512 MB of expanded data. Save or discard drafts, then import a smaller batch.');
  this.bytes+=count;
 }
 consumeMetadata(count:number){
  if(!Number.isSafeInteger(count)||count<0||this.metadata+count>this.limits.metadata)throw Error('Combined draft metadata exceeds 20 MB. Import a smaller batch.');
  this.consumeBytes(count);this.metadata+=count;
 }
 addRows(count:number){
  if(!Number.isSafeInteger(count)||count<0||this.rows+count>this.limits.rows)throw Error('Review queue exceeds 50,000 records. Save or discard drafts first.');
  this.rows+=count;
 }
 addAsset(key:string){if(this.assets.has(key))return;if(this.assets.size>=this.limits.assets)throw Error('Review queue exceeds 9,999 original files. Split this batch.');this.assets.add(key);}
 addRecognizedRows(rows:Row[]){this.addRows(rows.length);for(const row of rows)this.consumeMetadata(new TextEncoder().encode(JSON.stringify(row)).length);}
 seed(rows:Row[],assets:Map<string,Blob>){this.addRecognizedRows(rows);for(const [key,blob] of assets){this.addAsset(key);this.consumeBytes(blob.size);}return this;}
}
