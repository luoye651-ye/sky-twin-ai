// Same-origin website + authenticated APIs, ready for a domestic HTTPS tunnel.
// Uses the existing Java/Agent business services without an overseas
// routing service. The internal API gateway is loopback-only and secret-gated.
import http from 'node:http'
import { randomBytes } from 'node:crypto'
import { createReadStream, statSync, existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { once } from 'node:events'
import { createGzip } from 'node:zlib'
import { createGateway } from './public-gateway.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const mime = { '.html': 'text/html;charset=utf-8', '.js': 'text/javascript;charset=utf-8', '.css': 'text/css;charset=utf-8', '.json': 'application/json;charset=utf-8', '.glb': 'model/gltf-binary', '.bin': 'application/octet-stream', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.ico': 'image/x-icon' }

export async function createDomesticServer({ publicOrigin, port = 5182, staticRoot = path.join(root, 'frontend/dist'), upstreamRequest = http.request } = {}) {
  const origin = new URL(publicOrigin)
  if (origin.protocol !== 'https:' || origin.origin !== publicOrigin) throw new Error('Explicit HTTPS origin required')
  if (!existsSync(path.join(staticRoot, 'index.html'))) throw new Error('Build frontend before starting the domestic demo')
  const secret = randomBytes(32).toString('base64url')
  const api = createGateway({ origins: [publicOrigin], port: 0, tunnelSecret: secret, request: upstreamRequest })
  await once(api, 'listening')
  const server = http.createServer((req, res) => {
    res.setHeader('X-Content-Type-Options', 'nosniff')
    res.setHeader('Referrer-Policy', 'same-origin')
    const fail = (code, message) => { res.writeHead(code, { 'Content-Type': 'application/json;charset=utf-8', 'Cache-Control': 'no-store' }); res.end(JSON.stringify({ code, msg: message, detail: message })) }
    const localPort = server.address().port
    const localHosts = new Set([`127.0.0.1:${localPort}`, `localhost:${localPort}`])
    const host = req.headers.host
    if (host !== origin.host && !localHosts.has(host)) return fail(403, '未配置的访问域名')
    if (host === origin.host && req.headers['x-forwarded-proto'] !== 'https') return fail(426, '请使用配置的 HTTPS 演示地址')
    const requestOrigin = req.headers.origin
    if (requestOrigin && requestOrigin !== publicOrigin && ![...localHosts].some(v => requestOrigin === 'http://' + v)) return fail(403, '不允许的页面来源')
    let pathname
    try {
      pathname = decodeURIComponent(req.url.split('?')[0])
      if (!pathname.startsWith('/') || pathname.startsWith('//') || pathname.includes('\\') || /[\x00-\x20\x7f]/.test(pathname) || pathname.split('/').some(v => v.startsWith('.'))) throw new Error('path')
    } catch { return fail(400, '无效的请求路径') }
    if (/^\/(java-api|agent-api)(\/|$)/.test(pathname)) {
      const headers = { host: `127.0.0.1:${api.address().port}`, origin: publicOrigin, 'x-skytwin-gateway': secret }
      for (const key of ['authorization', 'content-type', 'content-length', 'accept']) if (req.headers[key]) headers[key] = req.headers[key]
      const upstream = http.request({ hostname: '127.0.0.1', port: api.address().port, path: req.url, method: req.method, headers }, reply => {
        const responseHeaders = { 'Cache-Control': 'no-store' }
        for (const key of ['content-type', 'content-disposition', 'content-encoding']) if (reply.headers[key]) responseHeaders[key] = reply.headers[key]
        res.writeHead(reply.statusCode || 502, responseHeaders); reply.pipe(res)
      })
      upstream.on('error', () => { if (!res.headersSent) fail(502, '本机业务网关未连接'); else res.destroy() })
      req.on('aborted', () => upstream.destroy()); res.on('close', () => upstream.destroy()); req.pipe(upstream); return
    }
    if (!['GET', 'HEAD'].includes(req.method)) return fail(405, '不支持的请求方法')
    if (pathname === '/deployment-config.js') {
      res.writeHead(200, { 'Content-Type': mime['.js'], 'Cache-Control': 'no-store' })
      res.end(req.method === 'HEAD' ? '' : "window.SKYTWIN_DEPLOYMENT = { apiOrigin: '' };\n"); return
    }
    const filename = path.resolve(staticRoot, '.' + pathname)
    if (!filename.startsWith(path.resolve(staticRoot) + path.sep) && filename !== path.resolve(staticRoot)) return fail(400, '无效的文件路径')
    let selected = filename
    try { if (!statSync(selected).isFile()) throw new Error('not a file') }
    catch {
      if (path.extname(pathname)) return fail(404, '资源不存在')
      selected = path.join(staticRoot, 'index.html')
    }
    const stat = statSync(selected)
    const extension = path.extname(selected)
    const etag = `W/"${stat.size.toString(16)}-${Math.trunc(stat.mtimeMs).toString(16)}"`
    const compressed = /\bgzip\b/.test(req.headers['accept-encoding'] || '') && /\.(json|js|css|svg|html)$/.test(selected) && stat.size > 1024
    const responseHeaders = { 'Content-Type': mime[extension] || 'application/octet-stream', 'Cache-Control': extension === '.html' ? 'no-store' : 'public,max-age=0,must-revalidate', ETag: etag, Vary: 'Accept-Encoding', ...(compressed ? { 'Content-Encoding': 'gzip' } : {}) }
    if (req.headers['if-none-match'] === etag && extension !== '.html') { res.writeHead(304, responseHeaders); res.end(); return }
    res.writeHead(200, responseHeaders)
    if (req.method === 'HEAD') res.end()
    else {
      const source = createReadStream(selected).on('error', () => res.destroy())
      const gzip = compressed ? createGzip() : undefined
      res.on('close', () => { source.destroy(); gzip?.destroy() })
      if (gzip) source.pipe(gzip.on('error', () => res.destroy())).pipe(res)
      else source.pipe(res)
    }
  })
  try { server.listen(port, '127.0.0.1'); await once(server, 'listening') }
  catch (error) { api.closeAllConnections(); api.close(); throw error }
  return { server, api, close() { server.closeAllConnections(); server.close(); api.closeAllConnections(); api.close() } }
}

if (process.argv[1] && import.meta.url === new URL('file:///' + process.argv[1].replaceAll('\\', '/')).href) {
  const settings = JSON.parse(readFileSync(path.join(root, '.runtime/domestic-demo.json'), 'utf8').replace(/^\uFEFF/, ''))
  const service = await createDomesticServer({ publicOrigin: settings.publicOrigin })
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => service.close())
  console.log('Domestic demonstration gateway ready on 127.0.0.1:5182')
}
