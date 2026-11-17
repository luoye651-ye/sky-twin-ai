// A loopback HTTP gateway for the public demonstration. No static files, admin
// APIs, SQL/Redis ports, arbitrary URLs, cookies or local credentials are served.
import http from 'node:http'
import { createHmac } from 'node:crypto'

const publicJava = new Map([
  ['/captchaImage', ['GET']], ['/login', ['POST']],
  ['/logout', ['POST']], ['/getInfo', ['GET']],
])
const methods = new Set(['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'PATCH'])
const bodyLimit = 12 * 1024 * 1024

export function routeFor(rawUrl, method) {
  if (!methods.has(method) || !rawUrl.startsWith('/') || rawUrl.startsWith('//')) return null
  let decoded
  try { decoded = decodeURIComponent(rawUrl.split('?')[0]) } catch { return null }
  if (/%(?:2f|5c|25)/i.test(rawUrl.split('?')[0]) || decoded.includes('\\') || decoded.includes('#') || decoded.split('/').some(p => p === '.' || p === '..') || /[\x00-\x20\x7f]/.test(decoded)) return null
  const [pathname, query = ''] = rawUrl.split('?')
  if (pathname.startsWith('/java-api/')) {
    const target = pathname.slice('/java-api'.length)
    if (!(publicJava.get(target)?.includes(method) || /^\/sky\//.test(target))) return null
    return { port: 8081, path: target + (query ? '?' + query : ''), authenticated: !['/captchaImage', '/login'].includes(target) }
  }
  if (pathname.startsWith('/agent-api/')) {
    const target = pathname.slice('/agent-api'.length)
    if (!/^\/(health|chat|workbench|vision-chat)(\/|$)/.test(target)) return null
    return { port: 8002, path: target + (query ? '?' + query : ''), authenticated: target !== '/health' }
  }
  return null
}

export function createGateway({ origins, port = 5181, host = '127.0.0.1', request = http.request, loginUser = 'sky_demo', tunnelSecret = '' } = {}) {
  if (!origins?.length || origins.some(v => new URL(v).origin !== v || !/^https?:\/\//.test(v))) throw new Error('Explicit Site origins required')
  const allowed = new Set(origins)
  let windowStart = Date.now(), loginCount = 0
  return http.createServer(async (req, res) => {
    const origin = req.headers.origin
    res.setHeader('X-Content-Type-Options', 'nosniff')
    res.setHeader('Cache-Control', 'no-store')
    res.setHeader('Vary', 'Origin')
    const fail = (status, message) => { res.writeHead(status, { 'Content-Type': 'application/json;charset=utf-8' }); res.end(JSON.stringify({ code: status, msg: message, detail: message })) }
    if (req.method === 'GET' && req.url.startsWith('/_gateway/ping?')) {
      const challenge = new URL(req.url, 'http://127.0.0.1').searchParams.get('challenge') || ''
      if (!tunnelSecret || !/^[a-f0-9-]{36}$/.test(challenge)) return fail(400, 'Invalid challenge')
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ signature: createHmac('sha256', tunnelSecret).update(challenge).digest('hex') })); return
    }
    if (tunnelSecret && req.headers['x-skytwin-gateway'] !== tunnelSecret) return fail(401, '请通过演示站点访问')
    if (origin && !allowed.has(origin)) return fail(403, '不允许的页面来源')
    if (origin) {
      res.setHeader('Access-Control-Allow-Origin', origin)
      res.setHeader('Access-Control-Expose-Headers', 'Content-Type,Content-Disposition')
    }
    const requestedMethod = req.method === 'OPTIONS' ? req.headers['access-control-request-method'] : req.method
    const route = routeFor(req.url, requestedMethod)
    if (!route) return fail(404, '公网入口未开放此接口')
    if (req.method === 'OPTIONS') {
      const requested = (req.headers['access-control-request-headers'] || '').toLowerCase().split(',').map(v => v.trim()).filter(Boolean)
      if (!origin || requested.some(v => !['authorization', 'content-type', 'accept'].includes(v))) return fail(403, '预检请求未获允许')
      res.writeHead(204, { 'Access-Control-Allow-Methods': 'GET,HEAD,POST,PUT,DELETE,PATCH,OPTIONS', 'Access-Control-Allow-Headers': 'Authorization,Content-Type,Accept', 'Access-Control-Max-Age': '600' }); res.end(); return
    }
    const authorization = req.headers.authorization
    if (route.authenticated && (!authorization || !/^Bearer [\x21-\x7e]{1,8192}$/.test(authorization))) return fail(401, '请先登录平台')
    const length = Number(req.headers['content-length'] || 0)
    if (!Number.isSafeInteger(length) || length < 0 || length > bodyLimit) return fail(413, '上传内容过大')
    if (Date.now() - windowStart > 60000) { windowStart = Date.now(); loginCount = 0 }
    if (route.path === '/login' && ++loginCount > 30) return fail(429, '登录请求过于频繁，请稍后重试')
    let loginBody
    if (route.port === 8081 && route.path === '/login') {
      try {
        const chunks = []; let bytes = 0
        for await (const chunk of req) { bytes += chunk.length; if (bytes > 8192) return fail(413, '登录内容过大'); chunks.push(chunk) }
        loginBody = Buffer.concat(chunks)
        if (JSON.parse(loginBody.toString('utf8')).username !== loginUser) return fail(403, '公网入口仅允许专用演示账号登录')
      } catch { return fail(400, '登录请求格式无效') }
    }
    // Copy only application headers; strip proxy identity and local cookies.
    // Origin was checked against the exact Site above. Normalize it to the
    // Agent's existing local frontend origin, keeping the Agent loopback-only.
    const headers = { host: `127.0.0.1:${route.port}`, origin: 'http://127.0.0.1:5173' }
    for (const key of ['authorization', 'content-type', 'content-length', 'accept']) if (req.headers[key]) headers[key] = req.headers[key]
    const upstream = request({ hostname: '127.0.0.1', port: route.port, path: route.path, method: req.method, headers }, reply => {
      const responseHeaders = {}
      for (const key of ['content-type', 'content-disposition', 'content-encoding']) if (reply.headers[key]) responseHeaders[key] = reply.headers[key]
      res.writeHead(reply.statusCode || 502, responseHeaders)
      reply.pipe(res)
    })
    let count = 0
    req.on('data', chunk => { count += chunk.length; if (count > bodyLimit) { upstream.destroy(); if (!res.headersSent) fail(413, '上传内容过大'); req.destroy() } })
    upstream.on('error', () => { if (!res.headersSent) fail(502, '本机业务服务尚未连接'); else res.destroy() })
    req.on('aborted', () => upstream.destroy())
    res.on('close', () => upstream.destroy())
    if (loginBody) upstream.end(loginBody)
    else req.pipe(upstream)
  }).listen(port, host)
}

if (process.argv[1] && import.meta.url === new URL('file:///' + process.argv[1].replaceAll('\\', '/')).href) {
  const origins = (process.env.SKYTWIN_PUBLIC_ORIGINS || '').split(',').map(v => v.trim()).filter(Boolean)
  if (!process.env.SKYTWIN_TUNNEL_SECRET) throw new Error('Tunnel gateway secret required')
  const server = createGateway({ origins, tunnelSecret: process.env.SKYTWIN_TUNNEL_SECRET })
  server.on('listening', () => console.log('SkyTwin API-only gateway ready on 127.0.0.1:5181'))
}
