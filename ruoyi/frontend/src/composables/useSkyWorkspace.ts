import { computed, onMounted, onUnmounted, shallowRef } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { skyRequest } from '@/api/sky'
import { getToken } from '@/utils/auth'
import useUserStore from '@/store/modules/user'
import { emptySnapshot } from '@sky/sky'
import { subscribeSky } from '@sky/skyStream'

export function useSkyWorkspace(kind: string) {
  const snapshot = shallowRef(emptySnapshot())
  const connected = shallowRef(false)
  const error = shallowRef('')
  const loading = shallowRef(false)
  const query = shallowRef('')
  const user = useUserStore()
  const canManage = computed(() => user.permissions.includes('*:*:*') || user.permissions.includes('sky:manage'))
  const canOperate = computed(() => user.permissions.includes('*:*:*') || user.permissions.includes('sky:operate'))
  const rows = computed(() => {
    const records = (snapshot.value as any)[kind] as Record<string, any>[] ?? []
    const keyword = query.value.trim().toLowerCase()
    return keyword ? records.filter(row => JSON.stringify(row).toLowerCase().includes(keyword)) : records
  })
  let stop: (() => void) | undefined
  async function refresh() {
    loading.value = true
    try { snapshot.value = (await skyRequest('/snapshot')).data; error.value = '' }
    catch (e) { error.value = e instanceof Error ? e.message : '读取业务数据失败' }
    finally { loading.value = false }
  }
  async function mutate(path: string, method: string, data?: unknown) {
    await skyRequest(path, method, data)
    await refresh()
    ElMessage.success('操作成功，业务数据已保存')
  }
  async function remove(row: Record<string, any>) {
    try {
      await ElMessageBox.confirm(`移除 ${row.name}？历史数据将保留。`, '移除资源', { type: 'warning' })
      await mutate(`/${kind}/${encodeURIComponent(row.id)}`, 'delete')
    } catch (e) { if (e !== 'cancel' && e !== 'close') error.value = e instanceof Error ? e.message : '操作失败' }
  }
  onMounted(() => {
    void refresh()
    stop = subscribeSky({ url: `${import.meta.env.VITE_APP_BASE_API}/sky/stream`, getToken, onSnapshot: value => { snapshot.value = value; error.value = '' }, onConnection: value => { connected.value = value }, onUnauthorized: () => { error.value = '登录已过期或没有业务权限，请重新登录' }, onError: message => { error.value = message } })
  })
  onUnmounted(() => stop?.())
  return { snapshot, connected, error, loading, query, rows, canManage, canOperate, refresh, mutate, remove }
}
