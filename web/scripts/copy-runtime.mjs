import {copyFile,mkdir,readdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const root=new URL('../',import.meta.url);
await mkdir(new URL('public/ocr/',root),{recursive:true});
for(const name of ['ort-wasm-simd-threaded.wasm','ort-wasm-simd-threaded.mjs'])await copyFile(new URL('node_modules/onnxruntime-web/dist/'+name,root),new URL('public/ocr/'+name,root));
console.log('Copied pinned ONNX runtime assets.');
await mkdir(new URL('public/licenses/',root),{recursive:true});
for(const name of ['onnxruntime-web','onnxruntime-common','pdfjs-dist','@zip.js/zip.js']){
 const dir=new URL('node_modules/'+name+'/',root),files=await readdir(dir);
 for(const file of files.filter(f=>/^(license|notice)(\.|$)/i.test(f)))await copyFile(new URL(file,dir),new URL('public/licenses/'+name.replaceAll('/','-').replace('@','')+'-'+file,root));
}
