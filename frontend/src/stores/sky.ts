import { apiUrl } from '../api/endpoint.ts'
import { computed, shallowRef } from 'vue'
import { defineStore } from 'pinia'
import { emptySnapshot } from '../../../shared/sky'
import { subscribeSky } from '../../../shared/skyStream'
import { getSkyToken, setSkyToken, javaRequest } from '../api/sky'
export const useSkyStore = defineStore('sky', () => {
  const snapshot = shallowRef(emptySnapshot())
  const username = shallowRef('')
  const permissions = shallowRef<string[]>([])
  const authorized = shallowRef(false)
  const connected = shallowRef(false)
  const loading = shallowRef(false)
  const error = shallowRef('')
  const canOperate = computed(() => permissions.value.includes('*:*:*') || permissions.value.includes('sky:operate'))
  let stop: (() => void) | undefined
  let initializing: Promise<void> | undefined
  function disconnect() { stop?.(); stop = undefined; connected.value = false }
  async function refresh() { snapshot.value = (await javaRequest('/sky/snapshot')).data }
  async function authenticate() {
    loading.value = true
    try {
      const info = await javaRequest('/getInfo')
      username.value = info.user.userName; permissions.value = info.permissions
      if (!permissions.value.includes('*:*:*') && !permissions.value.includes('sky:read')) throw new Error('此账号没有低空业务权限，请由管理员分配低空角色')
      await refresh(); authorized.value = true; error.value = ''; disconnect()
      stop = subscribeSky({ url: apiUrl('/java-api/sky/stream'), getToken: getSkyToken, onSnapshot: value => { snapshot.value = value; error.value = '' }, onConnection: value => { connected.value = value }, onUnauthorized: () => { disconnect(); authorized.value = false; error.value = '登录过期或权限不足，请重新登录' }, onError: message => { error.value = message } })
    } catch (e) { authorized.value = false; error.value = e instanceof Error ? e.message : '登录校验失败' }
    finally { loading.value = false }
  }
  function initialize() {
    if (!initializing && getSkyToken()) initializing = authenticate().finally(() => { initializing = undefined })
    return initializing ?? Promise.resolve()
  }
  async function login(form: { username: string; password: string; code: string; uuid: string }) { const result = await javaRequest('/login', 'POST', form); setSkyToken(result.token); await authenticate() }
  async function logout() {
    try { await javaRequest('/logout', 'POST') }
    finally { disconnect(); setSkyToken(); authorized.value = false; username.value = ''; permissions.value = []; snapshot.value = emptySnapshot() }
  }
  async function operate(path: string, data: unknown) { await javaRequest(`/sky${path}`, 'POST', data); await refresh() }
  return { snapshot, username, permissions, authorized, connected, loading, error, canOperate, initialize, refresh, login, logout, disconnect, operate }
})
