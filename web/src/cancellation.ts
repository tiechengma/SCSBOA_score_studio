/** Reject waiting callers immediately; task-specific cleanup stops underlying work. */
export class Cancellation {
 private controller=new AbortController();
 get cancelled(){return this.controller.signal.aborted;}
 error(){return Error('Import cancelled. Nothing was saved.');}
 check(){if(this.cancelled)throw this.error();}
 cancel(){this.controller.abort();}
 onCancel(cleanup:()=>void){
  const invoke=()=>{try{cleanup();}catch{/* Cancellation must still reach every registered task. */}};
  if(this.cancelled){invoke();return ()=>{};}
  this.controller.signal.addEventListener('abort',invoke,{once:true});
  return ()=>this.controller.signal.removeEventListener('abort',invoke);
 }
 wait<T>(pending:Promise<T>):Promise<T>{
  return new Promise((resolve,reject)=>{
   const off=this.onCancel(()=>reject(this.error()));
   pending.then(value=>{off();if(this.cancelled)reject(this.error());else resolve(value);},error=>{off();reject(this.cancelled?this.error():error);});
  });
 }
}
