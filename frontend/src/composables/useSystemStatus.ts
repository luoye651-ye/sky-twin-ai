import { computed } from 'vue'
import { useSkyStore } from '../stores/sky'
export type SystemStatus = 'checking' | 'online' | 'warning' | 'offline'
export function useSystemStatus() {
  const sky = useSkyStore()
  const status = computed<SystemStatus>(() => sky.loading ? 'checking' : !sky.authorized ? 'warning' : sky.connected ? 'online' : 'offline')
  const statusText = computed(() => ({ checking: '检测中', online: '系统在线', warning: '待登录', offline: '连接恢复中' })[status.value])
  return { status, statusText }
}
