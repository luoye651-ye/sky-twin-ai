# 只读配送订单列表：手写接入步骤

日期：2026-10-16。目标是在原SkyTwin平台显示订单、加载/错误/空状态并支持手动刷新；不增加创建、调度或送达操作。

本次提供待你亲手接入的代码，没有替你覆盖业务源文件。示例的语法检查不等于页面运行验收，保存到指定位置后还要构建并联调。

## 文件职责

| 位置（均在 ./frontend/src 内） | 责任 | 数据契约 |
|---|---|---|
| api/logistics.ts | 已有请求封装，补订单类型 | 返回订单数组 |
| composables/useLogisticsOrders.ts | 加载、刷新、错误处理 | 返回orders/loading/error/loadOrders |
| components/logistics/LogisticsOrderTable.vue | 只展示表格 | props: orders、loading；无修改事件 |
| components/logistics/LogisticsOrderPanel.vue | 组合刷新按钮、提示和表格 | 调用composable，把数据传给表格 |
| views/Logistics/index.vue | 路由页面入口 | 只组合Panel |
| router/index.ts | 注册 /logistics | 懒加载页面 |

先做完一个文件再做下一个，不在这一轮顺手扩展其他功能。现有Element Plus和全局深色表格样式可以复用，无需安装依赖。

## 1. 修改已有 api/logistics.ts

完整位置：`./frontend/src/api/logistics.ts`。

保留请求方式，补上TypeScript数据类型和数组检查。可替换为：

```ts
import { javaRequest } from './sky'

// 描述后端返回的一条订单，字段名要与JSON一致。
export interface LogisticsOrder {
  id: string
  cargoName: string
  weight: number
  startStationName: string
  endStationName: string
  status: string
  taskStatus: string
  progress: number
  deadlineAt: string
}

// Promise<LogisticsOrder[]>：等待请求完成后，得到订单数组。
export async function listLogisticsOrders(): Promise<LogisticsOrder[]> {
  const result = await javaRequest('/sky/logistics/orders')
  if (!Array.isArray(result.data)) {
    throw new Error('订单列表返回格式不正确')
  }
  return result.data
}
```

这里的TypeScript `interface` 只描述数据形状，不会创建HTTP接口；真实GET接口仍在Java Controller。它也不替代运行时字段校验。本课只检查返回根数据是数组。

## 2. 新建请求状态逻辑

完整位置：`./frontend/src/composables/useLogisticsOrders.ts`。

```ts
import { onMounted, onUnmounted, shallowRef } from 'vue'
import { listLogisticsOrders, type LogisticsOrder } from '../api/logistics'

export function useLogisticsOrders() {
  const orders = shallowRef<LogisticsOrder[]>([])
  const loading = shallowRef(false)
  const error = shallowRef('')
  let active = true

  async function loadOrders() {
    // 上一次没结束时，不重复发请求。
    if (loading.value || !active) return
    loading.value = true
    error.value = ''
    try {
      const data = await listLogisticsOrders()
      if (active) orders.value = data
    } catch (e) {
      if (active) {
        orders.value = []
        error.value = e instanceof Error ? e.message : '订单加载失败'
      }
    } finally {
      // 成功或失败都结束加载状态。
      if (active) loading.value = false
    }
  }

  // 页面挂载后加载一次；本课暂不轮询。
  onMounted(loadOrders)
  // 离开页面后，忽略迟到响应；没有改动全局请求工具。
  onUnmounted(() => { active = false })
  return { orders, loading, error, loadOrders }
}
```

这段是本课重点：`try`成功赋值，`catch`显示错误，`finally`收尾。脚本中用 `.value` 读写响应式状态；Vue模板中自动解包，不用写 `.value`。

## 3. 新建表格组件

先新建 `components/logistics` 文件夹。

完整位置：`./frontend/src/components/logistics/LogisticsOrderTable.vue`。

```vue
<script setup lang="ts">
import type { LogisticsOrder } from '../../api/logistics'
import { statusLabels } from '@sky/sky'

// 表格接收父组件的数据，不自己请求或修改订单。
defineProps<{ orders: LogisticsOrder[]; loading: boolean }>()
const orderLabels: Record<string, string> = {
  created: '已创建', delivered: '已送达'
}
</script>

<template>
  <el-table
    v-loading="loading" :data="orders" row-key="id" stripe
    empty-text="暂无配送订单">
    <el-table-column prop="cargoName" label="货物" min-width="150" />
    <el-table-column prop="weight" label="重量 kg" width="100" />
    <el-table-column prop="startStationName" label="起点" min-width="140" />
    <el-table-column prop="endStationName" label="终点" min-width="140" />
    <el-table-column label="订单状态" width="110">
      <template #default="{ row }">
        {{ orderLabels[row.status] ?? row.status }}
      </template>
    </el-table-column>
    <el-table-column label="任务状态" width="110">
      <template #default="{ row }">
        {{ statusLabels[row.taskStatus] ?? row.taskStatus }}
      </template>
    </el-table-column>
    <el-table-column label="任务进度" min-width="160">
      <template #default="{ row }">
        <el-progress :percentage="Math.round(row.progress)" />
      </template>
    </el-table-column>
    <el-table-column prop="deadlineAt" label="截止时间" min-width="220" />
  </el-table>
</template>
```

`props`是父组件传来的输入；`:data="orders"`把数组交给表格，`prop="cargoName"`读取每条记录的该字段。`#default="{ row }"`允许自定义单元格，`row`就是当前这一行。

不要只显示一个模糊“状态”：`status`是订单状态，`taskStatus`是关联任务状态。它们的值和变化时机不同。进度只读取服务器返回值，不在前端模拟增加。

## 4. 新建组合组件

完整位置：`./frontend/src/components/logistics/LogisticsOrderPanel.vue`。

```vue
<script setup lang="ts">
import { useLogisticsOrders } from '../../composables/useLogisticsOrders'
import LogisticsOrderTable from './LogisticsOrderTable.vue'

const { orders, loading, error, loadOrders } = useLogisticsOrders()
</script>

<template>
  <section class="logistics-panel business-theme">
    <div class="page-heading">
      <div>
        <h1>配送订单</h1>
        <p>查看最近200条订单及关联任务状态，点击刷新获取最新数据。</p>
      </div>
      <el-button type="primary" :loading="loading" :disabled="loading" @click="loadOrders">
        刷新订单
      </el-button>
    </div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <LogisticsOrderTable v-else :orders="orders" :loading="loading" />
  </section>
</template>

<style scoped>
.logistics-panel { padding: 24px; }
</style>
```

数据向下传：`Panel → Table`；刷新按钮调用同一个 `loadOrders`。失败时显示错误，不把请求失败伪装成“没有订单”。

## 5. 新建路由入口页

完整位置：`./frontend/src/views/Logistics/index.vue`。

```vue
<script setup lang="ts">
import LogisticsOrderPanel from '../../components/logistics/LogisticsOrderPanel.vue'
</script>

<template>
  <LogisticsOrderPanel />
</template>
```

入口页只组合组件。数据请求在composable、展示在Table，避免以后把创建、派机和所有逻辑挤到index.vue。

## 6. 注册新路由

打开 `./frontend/src/router/index.ts`，在 `routes: [...]` 数组里新增以下对象；注意与前一个对象之间有逗号，不要覆盖原路由。

```ts
{
  path: '/logistics',
  name: 'Logistics',
  component: () => import('../views/Logistics/index.vue')
}
```

第一版先通过 [平台订单地址](http://127.0.0.1:5173/logistics) 访问，不修改顶部导航、不在若依5174访问这个新路由。未登录时会先显示平台已有登录面板。

## 7. 保存后的验收

在 `.\frontend` 执行：

```powershell
npm.cmd run build
```

它包含Vue/TypeScript检查和前端打包。开发服务器运行中时，保存前端文件通常会热更新，无需重新打包Java。本轮未修改Java接口。

保存后再做实际页面验收，不要仅凭编译通过就标记完成：

- 登录后进入5173/logistics，能显示表头和正确的空状态。
- Network出现GET `/java-api/sky/logistics/orders`，响应code=200、data是数组。
- 有真实测试订单时，货物、站点、重量、订单状态、任务状态与接口一致。
- 点击刷新只查询，不新增/修改订单；加载期间禁用重复点击。
- 请求失败显示错误，恢复后刷新可重新加载。当前onUnmounted只忽略迟到响应，没有取消底层fetch。
- 切换离开再进入页面会重新查询；不新增自动飞行或定时状态修改。

之前的接口验收脚本会清理它的订单，所以初次列表为空是正常情况。不要为了显示效果把假订单写成真实业务记录。需要一条可观察的订单时，再用已验收POST创建一条明确标识的演示订单。

本轮的学习目标：说明 `loadOrders → orders → props → el-table` 的数据流，理解加载、成功、失败分别怎样更新页面。
