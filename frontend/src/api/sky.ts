import { apiFetch } from './endpoint.ts'
import { tokenCookieName } from '../utils/runtime.ts'
export function getSkyToken() {
  const tokenCookie=tokenCookieName()
  const cookie = document.cookie.split('; ').find(value => value.startsWith(tokenCookie+'='))
  return cookie ? decodeURIComponent(cookie.slice(tokenCookie.length+1)) : undefined
}
export function setSkyToken(token?: string) {
  const tokenCookie=tokenCookieName()
  document.cookie = token ? `${tokenCookie}=${encodeURIComponent(token)}; path=/; SameSite=Lax` : `${tokenCookie}=; path=/; Max-Age=0; SameSite=Lax`
}
export async function javaRequest(path: string, method = 'GET', data?: unknown, signal?: AbortSignal) {
  const token = getSkyToken()
  let response: Response
  try {
    response = await apiFetch(`/java-api${path}`, { method, signal, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) }, ...(data ? { body: JSON.stringify(data) } : {}) })
  } catch {
    throw new Error('无法连接服务，请检查网络及指挥中心是否已启动')
  }
  let result
  try {
    result = await response.json()
  } catch {
    if (response.status >= 500) {
      throw new Error(`后端服务暂不可用（HTTP ${response.status}），请运行 ruoyi/scripts/start.ps1 启动服务后重试`)
    }
    throw new Error(`接口返回格式异常（HTTP ${response.status}），请检查后端服务与代理配置`)
  }
  if (!result || typeof result !== 'object' || typeof result.code !== 'number') {
    throw new Error(`接口返回格式异常（HTTP ${response.status}），请检查后端服务与代理配置`)
  }
  if (!response.ok || result.code !== 200) throw new Error(result.msg || `请求失败 (${response.status})`)
  return result
}
