import {spawn} from 'node:child_process';
import {setTimeout as sleep} from 'node:timers/promises';
import {resolve} from 'node:path';

const server=process.env.TRIP_BASE_URL?null:spawn(process.execPath,[resolve('tests/static-server.mjs')],{stdio:'ignore'});
let ready=false;
try{
 if(server){
  for(let attempt=0;attempt<50;attempt++){
   if(server.exitCode!==null)throw new Error('Preview server exited before tests');
   try{const response=await fetch('http://127.0.0.1:4173/trip-optimizer/');if(response.ok){ready=true;break}}catch{}
   await sleep(100);
  }
  if(!ready)throw new Error('Preview server did not become ready');
 }
 const result=await new Promise((resolveResult,reject)=>{
  const testProcess=spawn(process.execPath,[resolve('node_modules/@playwright/test/cli.js'),'test'],{stdio:'inherit',env:process.env});
  testProcess.on('error',reject);
  testProcess.on('exit',(code,signal)=>resolveResult(code??(signal?1:0)));
 });
 process.exitCode=result;
}finally{server?.kill()}
