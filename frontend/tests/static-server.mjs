import {createServer} from 'node:http';
import {readFile,stat} from 'node:fs/promises';
import {resolve,sep} from 'node:path';

const root=resolve('out');
const base='/trip-optimizer/';
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.ico':'image/x-icon','.woff2':'font/woff2'};
createServer(async (req,res)=>{
 const pathname=new URL(req.url||'/', 'http://127.0.0.1').pathname;
 if(!pathname.startsWith(base)){res.writeHead(404).end('Not found');return;}
 const relative=decodeURIComponent(pathname.slice(base.length));
 const full=resolve(root,relative||'index.html');
 if(full!==root&&!full.startsWith(root+sep)){res.writeHead(403).end('Forbidden');return;}
 try{
  const info=await stat(full);
  const target=info.isDirectory()?resolve(full,'index.html'):full;
  const body=await readFile(target);
  const ext=target.slice(target.lastIndexOf('.'));
  res.writeHead(200,{'content-type':types[ext]||'application/octet-stream','cache-control':'no-store'}).end(body);
 }catch{res.writeHead(404).end('Not found')}
}).listen(4173,'127.0.0.1',()=>console.log('Static Pages preview: http://127.0.0.1:4173/trip-optimizer/'));
