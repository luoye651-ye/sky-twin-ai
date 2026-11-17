<script setup lang="ts">
import { computed, ref } from 'vue'
import { useSkyStore } from '../../stores/sky'
import { useLogisticsOrders } from '../../composables/useLogisticsOrders'
import { useLogisticsActions } from '../../composables/useLogisticsActions'
import LogisticsOrderForm from './LogisticsOrderForm.vue'
import LogisticsOrderTable from './LogisticsOrderTable.vue'
import LogisticsActionDialog from './LogisticsActionDialog.vue'
import LogisticsDetailDialog from './LogisticsDetailDialog.vue'
import { deliveryStage } from './logisticsPresentation'

const sky = useSkyStore()
const { orders, loading, refreshing, error, updatedAt, loadOrders } = useLogisticsOrders()
const { createVisible, action, selectedOrder, busy, operationError, openCreate, openAction,
  closeAction, saveOrder, saveAction } = useLogisticsActions(orders, loadOrders)
const availableStations = computed(() => sky.snapshot.stations.filter(station => station.status === 'enabled'))
const detailId = ref('')
const search = ref('')
const stage = ref('')
const stages = ['待分配', '待起飞', '运输中', '待确认送达', '已送达', '已取消', '配送失败']
const filteredOrders = computed(() => {
  const text = search.value.trim().toLowerCase()
  return orders.value.filter(order => (!stage.value || deliveryStage(order) === stage.value)
    && (!text || [order.cargoName, order.id, order.startStationName, order.endStationName]
      .some(value => value.toLowerCase().includes(text))))
})
const summary = computed(() => ({
  pending: orders.value.filter(order => order.status !== 'delivered' && ['created', 'assigned'].includes(order.taskStatus)).length,
  running: orders.value.filter(order => order.taskStatus === 'executing').length,
  awaiting: orders.value.filter(order => order.status !== 'delivered' && order.taskStatus === 'completed').length,
  delivered: orders.value.filter(order => order.status === 'delivered').length
}))
</script>

<template>
  <section class="logistics-panel business-theme">
    <div class="page-heading">
      <div><span class="eyebrow">LOGISTICS CENTER</span><h1>城市物流配送</h1><p>创建订单 → 分配货运机 → 执行仿真 → 跟踪配送 → 确认送达</p></div>
      <div class="page-actions">
        <el-button v-if="sky.canOperate" type="primary" :disabled="busy" @click="openCreate">新建配送订单</el-button>
        <el-button :loading="refreshing" :disabled="busy" @click="loadOrders()">刷新订单</el-button>
      </div>
    </div>
    <div class="summary-grid">
      <div class="summary-card"><span>待调度</span><strong>{{ summary.pending }}</strong></div>
      <div class="summary-card"><span>运输中</span><strong>{{ summary.running }}</strong></div>
      <div class="summary-card"><span>待确认送达</span><strong>{{ summary.awaiting }}</strong></div>
      <div class="summary-card"><span>已送达</span><strong>{{ summary.delivered }}</strong></div>
    </div>
    <div class="filters">
      <el-input v-model="search" placeholder="搜索货物、订单编号或站点" clearable aria-label="搜索配送订单" />
      <el-select v-model="stage" placeholder="全部配送阶段" clearable aria-label="配送阶段">
        <el-option v-for="label in stages" :key="label" :label="label" :value="label" />
      </el-select>
      <span class="refresh-note">最近200条 · 每3秒自动更新<span v-if="updatedAt"> · {{ updatedAt }}</span></span>
    </div>
    <el-alert v-if="error" :title="`${error}；当前内容可能不是最新数据，请刷新重试`" type="error" :closable="false" />
    <LogisticsOrderTable :orders="filteredOrders" :loading="loading" :can-operate="sky.canOperate" :busy="busy"
      @operate="openAction" @detail="order => detailId = order.id" />
    <p class="simulation-note">当前为本地仿真配送，采用10倍时间与简化电量估算；飞行状态和完成结果由Java服务更新。</p>

    <el-dialog v-model="createVisible" title="新建配送订单" width="560px" destroy-on-close
      :close-on-click-modal="false" :close-on-press-escape="!busy" :show-close="!busy">
      <LogisticsOrderForm :stations="availableStations" :busy="busy" :server-error="operationError" @save="saveOrder" />
      <template #footer><el-button :disabled="busy" @click="createVisible = false">取消</el-button></template>
    </el-dialog>
    <LogisticsActionDialog v-if="action && selectedOrder" :key="`${selectedOrder.id}-${action}`"
      :action="action" :order="selectedOrder" :aircraft="sky.snapshot.aircraft" :busy="busy"
      :server-error="operationError" @close="closeAction" @save="saveAction" />
    <LogisticsDetailDialog v-if="detailId" :order-id="detailId" @close="detailId = ''" />
  </section>
</template>

<style scoped>
.logistics-panel { padding:24px; min-height:100%; }
.page-actions { display:flex; gap:12px; flex-wrap:wrap; }
.summary-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:16px; margin:22px 0; }
.summary-card { border:1px solid #173d52; border-radius:8px; padding:16px 22px; background:linear-gradient(110deg,#0b2535,#071620); display:flex; justify-content:space-between; align-items:center; }
.summary-card span { color:#8cb2c7; }.summary-card strong { color:#33caff; font-size:28px; }
.filters { display:flex; align-items:center; gap:14px; margin-bottom:18px; flex-wrap:wrap; }
.filters .el-input { width:310px; }.filters .el-select { width:180px; }
.refresh-note,.simulation-note { color:#7b9cb1; font-size:12px; }.refresh-note { margin-left:auto; }.simulation-note { margin-top:18px; }
.el-alert { margin-bottom:14px; }
@media(max-width:900px) { .summary-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }.refresh-note { margin-left:0; } }
</style>
