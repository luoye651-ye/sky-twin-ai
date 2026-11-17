import { computed, onUnmounted, ref, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useSkyStore } from '../stores/sky'
import { createLogisticsOrder, operateLogisticsOrder, type CreateLogisticsOrderInput,
  type LogisticsAction, type LogisticsActionInput, type LogisticsOrder } from '../api/logistics'
import { actionLabels } from '../components/logistics/logisticsPresentation'

export function useLogisticsActions(orders: Ref<LogisticsOrder[]>, reload: () => Promise<void>) {
  const sky = useSkyStore()
  const createVisible = ref(false)
  const action = ref<LogisticsAction | ''>('')
  const selected = ref<LogisticsOrder | null>(null)
  const busy = ref(false)
  const operationError = ref('')
  const selectedOrder = computed(() => orders.value.find(order => order.id === selected.value?.id) ?? selected.value)
  let active = true
  onUnmounted(() => { active = false })

  function openCreate() {
    if (busy.value || !sky.canOperate) return
    operationError.value = ''; createVisible.value = true
  }
  function openAction(kind: LogisticsAction, order: LogisticsOrder) {
    if (busy.value || !sky.canOperate) return
    operationError.value = ''; selected.value = order; action.value = kind
  }
  function closeAction() { if (!busy.value) action.value = '' }

  async function save(request: () => Promise<unknown>, success: string) {
    if (busy.value || !sky.canOperate) return
    busy.value = true; operationError.value = ''
    try { await request() }
    catch (e) {
      if (active) operationError.value = e instanceof Error ? e.message : '操作失败'
      busy.value = false
      return
    }
    if (!active) { busy.value = false; return }
    createVisible.value = false; action.value = ''
    ElMessage.success(success)
    try { await Promise.all([reload(), sky.refresh().catch(() => undefined)]) }
    finally { busy.value = false }
  }

  const saveOrder = (input: CreateLogisticsOrderInput) => save(() => createLogisticsOrder(input), '配送订单已创建')
  function saveAction(input: LogisticsActionInput) {
    const id = selectedOrder.value?.id, kind = action.value
    if (!id || !kind) return
    return save(() => operateLogisticsOrder(id, kind, input), `${actionLabels[kind]}成功`)
  }
  return { createVisible, action, selectedOrder, busy, operationError, openCreate, openAction, closeAction, saveOrder, saveAction }
}
