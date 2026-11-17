// Production-built UI gateway for the independent sample server; loopback only.
import http from 'node:http'
import { createReadStream, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../frontend/dist')
const mime={'.html':'text/html;charset=utf-8','.js':'application/javascript;charset=utf-8','.css':'text/css;charset=utf-8','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.woff2':'font/woff2','.glb':'model/gltf-binary','.bin':'application/octet-stream'}
http.createServer((req,res)=>{
  const url=new URL(req.url,'http://127.0.0.1:5180')
  const prefix=['/agent-api','/java-api'].find(p=>url.pathname.startsWith(p+'/'))
  if(prefix){
    const upstream=http.request({host:'127.0.0.1',port:8003,path:req.url.slice(prefix.length),method:req.method,headers:{...req.headers,host:'127.0.0.1:8003'}},reply=>{res.writeHead(reply.statusCode,reply.headers);reply.pipe(res)})
    upstream.on('error',()=>{if(!res.headersSent)res.writeHead(502,{'Content-Type':'application/json'});res.end(JSON.stringify({code:503,msg:'独立演示服务尚未启动',detail:'独立演示服务尚未启动'}))})
    req.on('aborted',()=>upstream.destroy());res.on('close',()=>upstream.destroy());req.pipe(upstream);return
  }
  if(!['GET','HEAD'].includes(req.method)){res.writeHead(405);res.end();return}
  if(url.pathname==='/'){res.writeHead(302,{Location:'/ai-workbench'});res.end();return}
  let filename
  try{filename=path.resolve(root,'.'+decodeURIComponent(url.pathname));if(!filename.startsWith(root+path.sep))throw Error('path')}catch{res.writeHead(400);res.end();return}
  try{
    if(!statSync(filename).isFile())throw Error('not file')
    if(path.extname(filename)==='.html'){
      const html=readFileSync(filename,'utf8').replace('<head>','<head><meta name="skytwin-demo" content="isolated">')
      res.writeHead(200,{'Content-Type':'text/html;charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(req.method==='HEAD'?'':html);return
    }
    res.writeHead(200,{'Content-Type':mime[path.extname(filename)]||'application/octet-stream','X-Content-Type-Options':'nosniff'});if(req.method==='HEAD')res.end();else createReadStream(filename).pipe(res)
  }catch{
    if(path.extname(url.pathname)){res.writeHead(404);res.end();return}
    try{const html=readFileSync(path.join(root,'index.html'),'utf8').replace('<head>','<head><meta name="skytwin-demo" content="isolated">');res.writeHead(200,{'Content-Type':'text/html;charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(req.method==='HEAD'?'':html)}catch{res.writeHead(503);res.end('请先构建frontend')}
  }
}).listen(5180,'127.0.0.1',()=>process.stdout.write('Isolated sample UI: http://127.0.0.1:5180/ai-workbench\n'))
