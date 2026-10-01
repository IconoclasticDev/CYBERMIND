import fs from 'node:fs/promises';
import path from 'node:path';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';
const work=path.resolve('artifacts/track_e/slides');
const p=await PresentationFile.importPptx(await FileBlob.load(path.join(work,'output/CYBERMIND_demo.pptx')));
for(let i=0;i<p.slides.items.length;i++){const b=await p.export({slide:p.slides.items[i],format:'png',scale:1});await fs.writeFile(path.join(work,`preview/slide-${i+1}.png`),new Uint8Array(await b.arrayBuffer()));}
await fs.writeFile(path.join(work,'preview/index.html'),'<!doctype html><html><meta charset="utf-8"><title>CYBERMIND five-slide preview</title><style>body{margin:0;background:#07101b;color:white;font:16px Arial}main{max-width:1280px;margin:auto}img{width:100%;display:block;margin:20px 0}h1{padding:20px;font-size:24px}</style><main><h1>CYBERMIND · five-slide preview</h1>'+Array.from({length:5},(_,i)=>`<img src="slide-${i+1}.png" alt="Slide ${i+1}">`).join('')+'</main></html>');
console.log('Rendered final deck: '+p.slides.items.length+' slides');
