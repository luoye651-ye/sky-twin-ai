import type { Snapshot } from './sky'

interface Options {
  url: string; getToken: () => string | undefined;
  onSnapshot: (snapshot: Snapshot) => void; onConnection: (online: boolean) => void;
  onUnauthorized: () => void; onError?: (message: string) => void
}
/** Fetch supports Authorization headers; tokens never enter query strings. */
export function subscribeSky(options: Options) {
  let stopped = false
  let controller: AbortController | null = null
  let timer: ReturnType<typeof setTimeout> | undefined
  let delay = 1000
  async function connect() {
    if (stopped) return
    const token = options.getToken()
    if (!token) { options.onUnauthorized(); return }
    controller = new AbortController()
    try {
      const response = await fetch(options.url, { headers: { Authorization: `Bearer ${token}`, Accept: 'text/event-stream' }, signal: controller.signal })
      if (!response.ok || !response.headers.get('content-type')?.includes('text/event-stream')) {
        let code = response.status
        try { code = (await response.json()).code ?? code } catch { /* no JSON error body */ }
        if (code === 401 || code === 403) { stopped = true; options.onUnauthorized(); return }
        throw new Error(`实时服务不可用 (${code})`)
      }
      if (!response.body) throw new Error('浏览器不支持实时数据流')
      delay = 1000
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (!stopped) {
        const { value, done } = await reader.read()
        if (done) break
        buffer = (buffer + decoder.decode(value, { stream: true })).replace(/\r\n/g, '\n')
        let separator: number
        while ((separator = buffer.indexOf('\n\n')) >= 0) {
          const frame = buffer.slice(0, separator)
          buffer = buffer.slice(separator + 2)
          const data = frame.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n')
          if (data) {
            options.onSnapshot(JSON.parse(data) as Snapshot)
            options.onConnection(true)
          }
        }
        if (buffer.length > 5_000_000) throw new Error('实时数据帧超过允许大小')
      }
    } catch (error) {
      if (!stopped) { options.onConnection(false); options.onError?.(error instanceof Error ? error.message : '实时连接中断') }
    } finally {
      if (!stopped) { timer = setTimeout(connect, delay); delay = Math.min(delay * 2, 15000) }
    }
  }
  void connect()
  return () => { stopped = true; controller?.abort(); if (timer) clearTimeout(timer); options.onConnection(false) }
}
