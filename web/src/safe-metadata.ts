/** Validate extension metadata too, before recursive equality/clone/storage operations. */
export function assertSafeMetadata(root:unknown){
  const pending:{value:unknown;depth:number}[]=[{value:root,depth:0}],seen=new WeakSet<object>();
  let nodes=0;
  while(pending.length){
    const {value,depth}=pending.pop()!;
    if(++nodes>20000||depth>16)throw Error('Record metadata is too complex or deeply nested.');
    if(value===null||typeof value==='string'||typeof value==='boolean')continue;
    if(typeof value==='number'&&Number.isFinite(value))continue;
    if(typeof value!=='object'||seen.has(value))throw Error('Record metadata must contain ordinary JSON values without cycles.');
    seen.add(value);
    for(const key in value){
      if(!Object.hasOwn(value,key))continue;
      if(['__proto__','constructor','prototype'].includes(key))throw Error('Unsafe metadata key.');
      if(nodes+pending.length>=20000)throw Error('Record metadata is too complex or deeply nested.');
      pending.push({value:(value as Record<string,unknown>)[key],depth:depth+1});
    }
  }
}
