import { onMounted,onUnmounted, shallowRef } from 'vue'
import { listLogisticsOrders, type LogisticsOrder } from '../api/logistics'

export function useLogisticsOrders() {
    const orders = shallowRef<LogisticsOrder[]>([]) //订单数组
    const loading = shallowRef(false) //是否正在加载
    const refreshing = shallowRef(false)
    const updatedAt = shallowRef('')
    const error = shallowRef('') //错误提示
    let active = true
    let inFlight: Promise<void> | undefined
    let again = false
    let timer: ReturnType<typeof setInterval> | undefined
    
    async function refresh(showLoading: boolean): Promise<void> {
        if (!active) return
        if (inFlight) { again = true; return inFlight }
        loading.value = showLoading
        refreshing.value = true
        inFlight = (async () => {
            do {
                again = false
                try {
                    const data = await listLogisticsOrders()
                    if (active) {
                        orders.value = data
                        error.value = ''
                        updatedAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
                    }
                } catch (e) {
                    // Retain the last snapshot and explicitly show the refresh error.
                    if (active) error.value = e instanceof Error ? e.message : '订单加载失败'
                }
            } while (again && active)
        })()
        try { await inFlight }
        finally {
            inFlight = undefined
            if (active) { loading.value = false; refreshing.value = false }
        }
    }
    const loadOrders = () => refresh(true)
    onMounted(() => {
        void loadOrders()
        timer = setInterval(() => { if (!refreshing.value) void refresh(false) }, 3000)
    })
    onUnmounted(() => { active = false; clearInterval(timer) })
    return { orders, loading, refreshing, error, updatedAt, loadOrders }
}
