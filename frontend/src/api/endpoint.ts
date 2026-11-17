declare global {
  interface Window { SKYTWIN_DEPLOYMENT?: { apiOrigin?: string } }
}

// Local development keeps Vite's same-origin proxies. Hosted builds use the
// HTTPS gateway declared by deployment-config.js, never a visitor's localhost.
export function apiUrl(path: string): string {
  if (!/^\/(?:java-api|agent-api)\//.test(path)) throw new Error('无效的业务接口路径')
  const origin = typeof window === 'undefined' ? '' : window.SKYTWIN_DEPLOYMENT?.apiOrigin || ''
  if (!origin) return path
  const parsed = new URL(origin)
  if (parsed.protocol !== 'https:' || parsed.origin !== origin) throw new Error('公网接口地址须为 HTTPS 来源')
  return origin + path
}

export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(apiUrl(path), init)
}
