# 五类场景业务开发：分阶段填空手册

这是一份供你亲手操作的教程。本次只新增这份文档，没有替你创建业务表、修改 Java 或接入页面。代码中的 `__填空名__` 必须先替换，再复制到对应源文件。示例按当前项目接口编写，尚未作为业务代码运行；每课都必须执行验收。

## 先确定开发方向

现有代码已完成五类任务的创建、分配、执行、取消、失败、完成，以及轨迹、报告、告警和权限。图中的下一阶段是给这些任务增加真正的业务对象。

| 顺序 | 场景 | 新增业务对象 | 管理端页面 | 完成后如何证明 |
|---|---|---|---|---|
| 1 | 城市物流配送 | 配送订单 | 订单创建、调度、跟踪、确认送达 | 订单关联任务，任务降落完成后才能确认送达 |
| 2 | 环境监测 | 巡检影像、识别结果、证据 | 影像上传、结果复核、异常报告 | 一次巡检产生带图片和位置的事件及报告 |
| 3 | 应急救援 | 救援事件、处置记录 | 事件上报、资源调度、处置归档 | 上报、侦察、物资投送、人工处置可追溯 |
| 4 | 空中通勤 | 航线、班次、预约 | 航线配置、班次管理、座位预约 | 预约进入班次，完成仿真运输且不会超卖 |
| 5 | 空域智能管控 | 三维区域、航点、冲突记录 | 区域配置、航线检查、冲突处置 | 禁飞区和两机冲突能被服务器发现并拦截 |

每课遵循：**规则 → 表 → 后端 → 接口 → 管理页 → 验收 → 大屏展示**。先在若依管理端做业务，再在原大屏展示业务，避免同时调试两套前端。

目录根是 `D:/cursor/project/sky-twin`。下文标为“相对位置”的路径用于在资源管理器定位；文件分工如下：

```text
ruoyi/backend/sql/                         新业务迁移 SQL
ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/
                                          Java 业务输入、服务、控制器
ruoyi/frontend/src/api/                    管理端接口封装
ruoyi/frontend/src/composables/            请求和页面状态
ruoyi/frontend/src/components/sky-twin/    表单、列表、业务容器
ruoyi/frontend/src/views/sky-twin/         路由入口，保持简短
shared/                                   两端可复用的 TypeScript 类型
frontend/src/components/business/         原大屏中的业务展示
```

原 `backend/` 是 FastAPI，不在这里再建一套订单数据库。Java + MySQL 继续拥有业务状态。

---

## 第一课：物流配送订单，从创建到送达

### 1.1 先把规则写清楚

请在笔记中补充：

```text
订单记录：货物名称、重量、起点、终点、配送时限、关联任务、创建人。
一个订单对应 ____ 个物流任务。
本课物流任务只能分配给 type = ____ 的飞行器。
载重不足、电量不足、飞行器被占用：由 ____ 校验。
飞行任务完成表示抵达并降落；订单送达还需要 ____ 确认。
任务未完成时，即使前端调用确认接口，服务器也必须 ____。
```

本课时限采用真实墙钟时间，飞行过程仍是现有的 10 倍时间仿真。调度前用服务端预计仿真耗时检查是否来得及；第一版不承诺现实航程续航模型。

订单保存业务事实 `created / delivered`，运输阶段从关联任务的 `created / assigned / executing / completed / cancelled / failed` 读取。这样不必在仿真每一帧复制一份“订单飞行状态”。

### 1.2 创建新表，不修改已有七张表

新建相对位置：`ruoyi/backend/sql/sky_twin_v2_logistics.sql`。

```sql
CREATE TABLE IF NOT EXISTS st_logistics_order (
    id varchar(40) PRIMARY KEY,
    cargo_name varchar(80) NOT NULL,
    weight decimal(10,2) NOT NULL,
    deadline_at datetime(3) NOT NULL,
    task_id varchar(40) NOT NULL UNIQUE,
    status varchar(20) NOT NULL DEFAULT 'created',
    created_by varchar(64) NOT NULL,
    created_time datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    delivered_by varchar(64),
    delivered_at datetime(3),
    FOREIGN KEY (task_id) REFERENCES st_task(id),
    INDEX idx_logistics_created(created_time)
) ENGINE=InnoDB;
```

在 Navicat 的 **127.0.0.1:3307 → sky_twin_ruoyi** 中打开新查询，粘贴并执行这一段。不要在图中的系统库 `mysql` 执行。保留 SQL 文件，后面才能在其他电脑重建。

验收：刷新表列表，看到 `st_logistics_order`；打开设计表，确认 `task_id` 的唯一索引和外键都存在。`UNIQUE` 表示一条任务不能绑定两个配送订单。

### 1.3 输入类：限制哪些字段可以从浏览器传入

新建相对位置：`ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/LogisticsInputs.java`。

```java
package com.ruoyi.skytwin;

import jakarta.validation.constraints.*;

public final class LogisticsInputs {
    private LogisticsInputs() {}

    public record Create(
        @NotBlank @Size(max=80) String cargoName,
        @NotNull @DecimalMin("0.01") @DecimalMax("10000") Double weight,
        @NotBlank @Size(max=40) String startStationId,
        @NotBlank @Size(max=40) String endStationId,
        @NotNull @Min(1) @Max(1440) Integer deadlineMinutes,
        @NotBlank @Size(max=500) String reason
    ) {}

    public record Dispatch(
        @NotBlank @Size(max=40) String aircraftId,
        @NotBlank @Size(max=500) String reason
    ) {}
}
```

观察：没有 `status`、`createdBy`、`taskId` 输入字段。这些由服务器决定，浏览器不能声称订单已经送达或者冒用其他创建人。

### 1.4 服务类：把订单和已有任务连接起来

新建同目录 `LogisticsService.java`。先理解构造函数：Spring 会把已有 `SkyRepository`、`SkyService` 注入进来，直接复用。

填空只在本节代码中替换；下面一共有 5 个。

```java
package com.ruoyi.skytwin;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import com.ruoyi.common.exception.ServiceException;

@Service
public class LogisticsService {
    private final SkyRepository db;
    private final SkyService sky;

    public LogisticsService(SkyRepository db, SkyService sky) {
        this.db = db;
        this.sky = sky;
    }

    private static void check(boolean ok, String message) {
        if (!ok) throw new ServiceException(message, 409);
    }

    private void audit(String id, String action, String reason, String actor) {
        db.update("INSERT INTO st_audit(entity_id,action,reason,actor) VALUES(?,?,?,?)",
            id, action, reason, actor);
    }

    public List<Map<String,Object>> list() {
        return db.rows("""
            SELECT o.*, t.status AS task_status, t.progress,
                   t.aircraft_id, t.updated_time AS task_updated_time,
                   s.name AS start_station_name, e.name AS end_station_name
            FROM st_logistics_order o
            JOIN st_task t ON t.id=o.task_id
            JOIN st_station s ON s.id=t.start_station_id
            JOIN st_station e ON e.id=t.end_station_id
            ORDER BY o.created_time DESC, o.id DESC LIMIT 200
            """);
    }

    @Transactional
    public String create(LogisticsInputs.Create x, String actor) {
        String orderId = "O-" + UUID.randomUUID().toString().replace("-", "");
        String taskId = sky.createTask(new SkyInputs.Task(
            "配送：" + x.cargoName(), "__TASK_TYPE__",
            x.startStationId(), x.endStationId(),
            x.weight(), 0, 10.0, 60.0, x.reason()
        ), actor);

        LocalDateTime deadline = LocalDateTime.now().plusMinutes(x.deadlineMinutes());
        db.update("""
            INSERT INTO st_logistics_order
              (id,cargo_name,weight,deadline_at,task_id,created_by)
            VALUES(?,?,?,?,?,?)
            """, orderId, x.cargoName(), x.weight(),
            Timestamp.valueOf(deadline), taskId, actor);
        audit(orderId, "order.create", x.reason(), actor);
        return orderId;
    }

    @Transactional
    public void dispatch(String id, LogisticsInputs.Dispatch x, String actor) {
        var order = db.one("SELECT * FROM st_logistics_order WHERE id=? FOR UPDATE", id);
        check("created".equals(order.get("status")), "订单已送达，不能重复调度");
        String taskId = order.get("taskId").toString();
        var task = db.one("SELECT * FROM st_task WHERE id=? FOR UPDATE", taskId);
        check("created".equals(task.get("status")), "仅待分配任务可以调度");

        var aircraft = db.one("SELECT * FROM st_aircraft WHERE id=? AND deleted=0", x.aircraftId());
        check("__AIRCRAFT_TYPE__".equals(aircraft.get("type")), "请选择货运无人机");
        int duration = ((Number) task.get("durationSeconds")).intValue();
        // Repository 把 SQL Timestamp 转为了 ISO 格式字符串。
        LocalDateTime deadline = LocalDateTime.parse(order.get("deadlineAt").toString());
        check(!LocalDateTime.now().plusSeconds(duration).isAfter(deadline),
            "预计无法在配送时限内完成仿真，请重新创建时限足够的订单");

        sky.taskAction(taskId, "__ASSIGN_ACTION__",
            new SkyInputs.Action(x.aircraftId(), x.reason()), actor);
        sky.taskAction(taskId, "__START_ACTION__",
            new SkyInputs.Action(null, x.reason()), actor);
        audit(id, "order.dispatch", x.reason(), actor);
    }

    @Transactional
    public void deliver(String id, String reason, String actor) {
        var order = db.one("SELECT * FROM st_logistics_order WHERE id=? FOR UPDATE", id);
        check("created".equals(order.get("status")), "已经确认送达，不能重复确认");
        var task = db.one("SELECT * FROM st_task WHERE id=? FOR UPDATE", order.get("taskId"));
        check("__COMPLETED_STATE__".equals(task.get("status")), "飞行任务尚未完成，不能确认送达");
        db.update("""
            UPDATE st_logistics_order
            SET status='delivered', delivered_by=?, delivered_at=NOW(3)
            WHERE id=?
            """, actor, id);
        audit(id, "order.deliver", reason, actor);
    }
}
```

为什么三个方法都有 `@Transactional`？创建任务成功但订单写入失败时，两者一起回滚；分配成功但启动失败时，分配也回滚，不能残留一架被占用的飞行器。这里调用的是注入的另一个 Spring 服务，能参加同一事务。

### 1.5 把“物流只能用货运机”放到共用入口

不能只靠新订单接口检查，因为现有任务管理页也能分配物流任务。

打开现有 `SkyService.java`，在 `taskAction` 的 `assign` 分支中找到：

```java
var a=db.one("SELECT * FROM st_aircraft WHERE id=? AND deleted=0 FOR UPDATE",x.aircraftId());
```

紧接它加入这一段，已有电量、载重、占用校验全部保留：

```java
if (s(t, "type").equals("logistics")) {
    require(s(a, "type").equals("cargo"), "物流配送任务必须分配货运无人机");
}
```

这是本课刻意收紧的规则：之前基础版允许普通无人机执行物流任务。后面如果要允许小型无人机配送，应明确修改业务规则，而不是只修改下拉框。

### 1.6 控制器：让网页可以调用服务

新建同目录 `LogisticsController.java`。

```java
package com.ruoyi.skytwin;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.access.prepost.PreAuthorize;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.enums.BusinessType;

@RestController
@RequestMapping("/sky/logistics/orders")
public class LogisticsController extends BaseController {
    private final LogisticsService service;
    public LogisticsController(LogisticsService service) { this.service = service; }

    @GetMapping
    @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult list() { return success(service.list()); }

    @PostMapping
    @PreAuthorize("@ss.hasPermi('sky:operate')")
    @Log(title="配送订单", businessType=BusinessType.INSERT)
    public AjaxResult create(@Valid @RequestBody LogisticsInputs.Create x) {
        return success((Object) service.create(x, getUsername()));
    }

    @PostMapping("/{id}/dispatch")
    @PreAuthorize("@ss.hasPermi('sky:operate')")
    @Log(title="订单调度", businessType=BusinessType.UPDATE)
    public AjaxResult dispatch(@PathVariable String id, @Valid @RequestBody LogisticsInputs.Dispatch x) {
        service.dispatch(id, x, getUsername());
        return success();
    }

    @PostMapping("/{id}/deliver")
    @PreAuthorize("@ss.hasPermi('sky:operate')")
    @Log(title="确认送达", businessType=BusinessType.UPDATE)
    public AjaxResult deliver(@PathVariable String id, @Valid @RequestBody SkyInputs.Action x) {
        service.deliver(id, x.reason(), getUsername());
        return success();
    }
}
```

注意 `success((Object) id)`：本项目的 `success(String)` 把字符串当消息，不会放进 `data`。已有 `SkyController.createTask` 就是这样写的。

先完成后端再做网页。项目根目录 PowerShell 逐条执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\stop.ps1 -Service backend
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\build.ps1 -Target backend
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\start.ps1 -Service backend
```

第二条必须出现 `BUILD SUCCESS` 才继续第三条。先停止 Java 是为了避免 Windows 锁住正在运行的 jar。

### 1.7 接口验收：先排除后端问题

在若依登录后，浏览器开发者工具 Network 中可以查看 `/getInfo` 请求的 `Authorization`。本地接口测试工具也可复用你自己的登录令牌；不要把令牌贴到聊天或提交到仓库。

| 操作 | Java 接口 | 请求体 |
|---|---|---|
| 列表 | GET `/sky/logistics/orders` | 无 |
| 创建 | POST `/sky/logistics/orders` | 下方 JSON |
| 调度并启动 | POST `/sky/logistics/orders/{订单id}/dispatch` | `aircraftId`、`reason` |
| 确认送达 | POST `/sky/logistics/orders/{订单id}/deliver` | `reason` |
| 查询轨迹 | GET `/sky/tasks/{任务id}/tracks` | 无 |

若依页面经 `/dev-api` 代理；接口工具直接访问 `http://127.0.0.1:8081` 时不加这个前缀。每个接口都需要 `Authorization: Bearer 你的令牌`。

```json
{
  "cargoName": "应急药品",
  "weight": 2,
  "startStationId": "S-01",
  "endStationId": "S-02",
  "deadlineMinutes": 10,
  "reason": "物流课程测试"
}
```

1. 创建返回 `data: "O-..."`，在列表中找到对应 `taskId`。
2. 未调度时尝试确认送达，应被拒绝。
3. 调度使用 `{ "aircraftId": "C-01", "reason": "满足载重和时限，安排配送" }`。
4. 稍后查询，服务端的任务状态应从 `executing` 变为 `completed`。
5. 发送确认送达请求，订单状态变为 `delivered`。
6. 打开 Navicat，看到订单、任务、轨迹、报告和审计记录。

若 `C-01` 正在执行旧任务，先等待其结束；不要直接在数据库中把其状态改成空闲。

### 1.8 管理端组件设计

本课组件分工：

| 文件 | 责任 | 输入/输出 |
|---|---|---|
| `LogisticsOrderForm.vue` | 填写订单 | props: 站点、busy；emit: create |
| `LogisticsOrderTable.vue` | 展示订单及操作 | props: 订单、飞行器、busy、canOperate；emit: dispatch、deliver、tracks |
| `LogisticsWorkspace.vue` | 组合表单和列表 | 调用 composable，传递 props，处理 emit |
| `useLogisticsOrders.ts` | 请求订单、定时刷新、错误和操作状态 | 返回 rows/error/busy/refresh/create/dispatch/deliver |
| `views/sky-twin/logistics/index.vue` | 页面入口 | 只组合 Workspace |

下面提供表单和接口的直接模板；列表和容器按小练习补齐，避免你一次照抄整个系统。

新建 `shared/logistics.ts`：

```ts
export interface CreateLogisticsOrder {
  cargoName: string
  weight: number
  startStationId: string
  endStationId: string
  deadlineMinutes: number
  reason: string
}

export interface LogisticsOrder {
  id: string
  cargoName: string
  weight: number
  deadlineAt: string
  status: 'created' | 'delivered'
  taskId: string
  taskStatus: string
  progress: number
  aircraftId: string | null
  startStationName: string
  endStationName: string
}
```

新建 `ruoyi/frontend/src/api/logistics.ts`：

```ts
import { skyRequest } from '@/api/sky'
import type { CreateLogisticsOrder, LogisticsOrder } from '@sky/logistics'

export async function listOrders(): Promise<LogisticsOrder[]> {
  return (await skyRequest('/logistics/orders')).data
}
export async function createOrder(data: CreateLogisticsOrder): Promise<string> {
  return (await skyRequest('/logistics/orders', 'post', data)).data
}
export function dispatchOrder(id: string, aircraftId: string, reason: string) {
  return skyRequest(`/logistics/orders/${encodeURIComponent(id)}/dispatch`, 'post', { aircraftId, reason })
}
export function deliverOrder(id: string, reason: string) {
  return skyRequest(`/logistics/orders/${encodeURIComponent(id)}/deliver`, 'post', { reason })
}
```

这里复用现有 `skyRequest`，它已经通过若依 request 工具携带令牌。不要另写一套未鉴权的 fetch。

新建 `ruoyi/frontend/src/components/sky-twin/LogisticsOrderForm.vue`：

```vue
<script setup lang="ts">
import { computed, reactive, shallowRef } from 'vue'
import type { Station } from '@sky/sky'
import type { CreateLogisticsOrder } from '@sky/logistics'

const props = defineProps<{ stations: Station[]; busy: boolean }>()
const emit = defineEmits<{ create: [data: CreateLogisticsOrder] }>()
const error = shallowRef('')
const form = reactive<CreateLogisticsOrder>({
  cargoName: '', weight: 2, startStationId: '', endStationId: '',
  deadlineMinutes: 10, reason: '配送演示'
})
const stations = computed(() => props.stations.filter(s => s.status === '__ENABLED__'))

function submit() {
  if (!form.cargoName.trim() || !form.reason.trim() || !form.startStationId || !form.endStationId) {
    error.value = '请填写货物名称、起终点和原因'; return
  }
  if (form.startStationId === form.endStationId) {
    error.value = '起终点不能相同'; return
  }
  error.value = ''
  emit('__CREATE_EVENT__', { ...form })
}
</script>

<template>
  <el-alert v-if="error" :title="error" type="error" :closable="false" />
  <el-form label-width="100px" @submit.prevent="submit">
    <el-form-item label="货物名称"><el-input v-model="form.cargoName" maxlength="80" /></el-form-item>
    <el-form-item label="重量 kg"><el-input-number v-model="form.weight" :min="0.01" :max="10000" :precision="2" /></el-form-item>
    <el-form-item label="起点">
      <el-select v-model="form.startStationId">
        <el-option v-for="s in stations" :key="s.id" :label="s.name" :value="s.id" />
      </el-select>
    </el-form-item>
    <el-form-item label="终点">
      <el-select v-model="form.endStationId">
        <el-option v-for="s in stations" :key="s.id" :label="s.name" :value="s.id" :disabled="s.id === form.startStationId" />
      </el-select>
    </el-form-item>
    <el-form-item label="时限 分钟"><el-input-number v-model="form.deadlineMinutes" :min="1" :max="1440" /></el-form-item>
    <el-form-item label="原因"><el-input v-model="form.reason" maxlength="500" /></el-form-item>
    <el-button native-type="submit" type="primary" :loading="busy" :disabled="busy">创建订单</el-button>
  </el-form>
</template>
```

**思考题：** 为什么使用 `reactive` 保存表单？为什么用 `computed` 筛选站点？为什么提交 `{ ...form }` 而不是让父组件修改子组件的表单？

### 1.9 请求状态 composable：你先填一个方法，再照着写两个

新建 `ruoyi/frontend/src/composables/useLogisticsOrders.ts`：

```ts
import { onMounted, onUnmounted, shallowRef } from 'vue'
import { createOrder, listOrders, dispatchOrder, deliverOrder } from '@/api/logistics'
import type { CreateLogisticsOrder, LogisticsOrder } from '@sky/logistics'

export function useLogisticsOrders() {
  const rows = shallowRef<LogisticsOrder[]>([])
  const busy = shallowRef(false)
  const error = shallowRef('')
  let reading = false
  let disposed = false
  let timer: ReturnType<typeof setInterval> | undefined

  async function refresh() {
    if (reading || disposed) return
    reading = true
    try {
      const next = await listOrders()
      if (!disposed) rows.value = next
    } catch (e) {
      if (!disposed) error.value = e instanceof Error ? e.message : '读取订单失败'
    } finally { reading = false }
  }

  async function run(action: () => Promise<unknown>) {
    if (busy.value) return
    busy.value = true; error.value = ''
    try { await action(); await refresh() }
    catch (e) { error.value = e instanceof Error ? e.message : '操作失败' }
    finally { busy.value = false }
  }

  function create(data: CreateLogisticsOrder) {
    return run(() => __CREATE_FUNCTION__(data))
  }
  function dispatch(id: string, aircraftId: string, reason: string) {
    return run(() => dispatchOrder(id, aircraftId, reason))
  }
  function deliver(id: string, reason: string) {
    return run(() => deliverOrder(id, reason))
  }

  onMounted(() => { void refresh(); timer = setInterval(() => void refresh(), 2000) })
  onUnmounted(() => { disposed = true; if (timer) clearInterval(timer) })
  return { rows, busy, error, refresh, create, dispatch, deliver }
}
```

这课的订单列表暂时每两秒查询一次；已有飞行器和任务仍用原 SSE。后面再把业务对象放入 SSE 快照，避免在学新业务时同时改消息机制。`reading` 避免慢请求堆积；成功提交时遇到正在读取的旧请求，下一次轮询会刷新最新列表。

### 1.10 列表练习：把 4 个按钮和真实状态连接

新建 `LogisticsOrderTable.vue`，基础框架如下。补全标有 `TODO` 的模板部分，可参考现有 `BusinessTable.vue` 中的 `el-table-column` 写法。

```vue
<script setup lang="ts">
import { computed, reactive } from 'vue'
import type { Aircraft } from '@sky/sky'
import type { LogisticsOrder } from '@sky/logistics'
const props = defineProps<{
  rows: LogisticsOrder[]; aircraft: Aircraft[]; busy: boolean; canOperate: boolean
}>()
const emit = defineEmits<{
  dispatch: [id: string, aircraftId: string]
  deliver: [id: string]
  tracks: [taskId: string]
}>()
const selected = reactive<Record<string, string>>({})
const cargoAircraft = computed(() => props.aircraft.filter(a => a.type === 'cargo' && a.status === 'idle'))

function stage(row: LogisticsOrder) {
  if (row.status === 'delivered') return '已送达'
  const labels: Record<string, string> = {
    created: '待调度', assigned: '已分配', executing: '运输中',
    completed: '待确认送达', failed: '运输失败', cancelled: '已取消'
  }
  return labels[row.taskStatus] ?? row.taskStatus
}
</script>
<template>
  <el-table :data="rows" row-key="id">
    <el-table-column prop="cargoName" label="货物" />
    <el-table-column prop="weight" label="重量 kg" />
    <el-table-column prop="startStationName" label="起点" />
    <el-table-column prop="endStationName" label="终点" />
    <el-table-column prop="deadlineAt" label="截止时间" />
    <el-table-column label="阶段"><template #default="{ row }">{{ stage(row) }}</template></el-table-column>
    <el-table-column label="操作" min-width="320">
      <template #default="{ row }">
        <!-- TODO 1：待调度且 canOperate 时显示下拉框和调度按钮 -->
        <!-- 下拉框 v-model="selected[row.id]"；选项用 cargoAircraft -->
        <!-- 按钮没有选择飞行器或 busy 时禁用 -->
        <!-- 点击 emit('dispatch', row.id, selected[row.id]) -->

        <!-- TODO 2：taskStatus === 'completed' 且 status !== 'delivered' -->
        <!-- 并且 canOperate 时显示确认送达；点击 emit('deliver', row.id) -->

        <el-button :disabled="busy" @click="emit('tracks', row.taskId)">查看轨迹</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>
```

TODO 1 的参考填法：

```vue
<template v-if="canOperate && row.taskStatus === 'created' && row.status === 'created'">
  <el-select v-model="selected[row.id]" placeholder="货运无人机" style="width:160px">
    <el-option v-for="a in cargoAircraft" :key="a.id" :label="a.name" :value="a.id" />
  </el-select>
  <el-button :disabled="busy || !selected[row.id]" @click="emit('dispatch', row.id, selected[row.id])">调度</el-button>
</template>
```

TODO 2 的填空：

```vue
<el-button
  v-if="canOperate && row.taskStatus === '__ALLOW_DELIVER__' && row.status !== 'delivered'"
  :disabled="busy"
  @click="emit('deliver', row.id)">
  确认送达
</el-button>
```

按钮条件只是交互提示；后端的 `deliver` 检查仍然必不可少。

### 1.11 容器与路由：把组件拼起来

新建 `LogisticsWorkspace.vue`：

```vue
<script setup lang="ts">
import { shallowRef } from 'vue'
import { skyRequest } from '@/api/sky'
import { useSkyWorkspace } from '@/composables/useSkyWorkspace'
import { useLogisticsOrders } from '@/composables/useLogisticsOrders'
import LogisticsOrderForm from './LogisticsOrderForm.vue'
import LogisticsOrderTable from './LogisticsOrderTable.vue'
import type { Track } from '@sky/sky'

const { snapshot, canOperate, error: skyError } = useSkyWorkspace('tasks')
const { rows, busy, error, create, dispatch, deliver, refresh } = useLogisticsOrders()
const tracks = shallowRef<Track[]>([])
const tracksOpen = shallowRef(false)
const tracksError = shallowRef('')
async function showTracks(taskId: string) {
  tracksError.value = ''
  try {
    tracks.value = (await skyRequest(`/tasks/${encodeURIComponent(taskId)}/tracks`)).data
    tracksOpen.value = true
  } catch (e) { tracksError.value = e instanceof Error ? e.message : '轨迹读取失败' }
}
function handleDispatch(id: string, aircraftId: string) {
  void dispatch(id, aircraftId, '人工调度：载重、电量与时限由服务器检查')
}
function handleDeliver(id: string) {
  void deliver(id, '现场确认货物送达（课程仿真）')
}
</script>
<template>
  <div class="app-container">
    <h2>物流配送订单</h2>
    <el-alert v-if="error || skyError || tracksError" :title="error || skyError || tracksError" type="error" :closable="false" />
    <LogisticsOrderForm v-if="canOperate" :stations="snapshot.stations" :busy="busy" @create="create" />
    <el-button :disabled="busy" @click="refresh">刷新订单</el-button>
    <LogisticsOrderTable
      :rows="rows" :aircraft="snapshot.aircraft" :busy="busy" :can-operate="canOperate"
      @dispatch="handleDispatch" @deliver="handleDeliver" @tracks="showTracks" />
    <el-dialog v-model="tracksOpen" title="轨迹记录" width="800px">
      <el-table :data="tracks">
        <el-table-column prop="recordedTime" label="时间" />
        <el-table-column prop="longitude" label="经度" />
        <el-table-column prop="latitude" label="纬度" />
        <el-table-column prop="altitude" label="高度 m" />
        <el-table-column prop="progress" label="进度 %" />
      </el-table>
    </el-dialog>
  </div>
</template>
```

注意：原因暂时是课程固定文本。基本流程通过后，再把调度、确认送达改成弹窗填写真实原因；可以参考现有 `TaskActionDialog.vue`。查看轨迹先做表格，不在这一步改三维地图。

新建 `ruoyi/frontend/src/views/sky-twin/logistics/index.vue`：

```vue
<script setup lang="ts">
import LogisticsWorkspace from '@/components/sky-twin/LogisticsWorkspace.vue'
</script>
<template><LogisticsWorkspace /></template>
```

在若依后台 **系统管理 → 菜单管理 → 低空业务 → 新增子菜单**：

```text
菜单类型：菜单
菜单名称：物流配送
路由地址：logistics
组件路径：sky-twin/logistics/index
权限字符：sky:read
是否缓存：否（本课依赖卸载清理定时器）
显示状态：显示
菜单状态：正常
```

超级管理员重新登录后应能看到菜单。给调度员和查看者使用时，还要在角色管理中勾选新菜单；按钮仍依赖已有 `sky:operate`。隐藏按钮并不能替代后端鉴权。

### 1.12 第一课验收，全部打勾才能继续

- [ ] 建订单后，数据库同时新增一条订单和一条 `logistics` 任务。
- [ ] 不调度直接确认送达：服务器拒绝，订单不变。
- [ ] 分配普通 `D-01`：新订单接口和原任务分配接口都拒绝。
- [ ] 把货物设为超过 C-01 的 20 kg 载重：创建可保存，但调度拒绝，C-01 不被占用。
- [ ] 低电量飞行器调度被拒绝；另一订单抢占正在执行的 C-01 被拒绝。
- [ ] 正常调度 C-01：原大屏显示服务器推送的位置和任务进度。
- [ ] 关闭大屏浏览器后，任务仍由 Java 完成。
- [ ] 任务完成后订单显示“待确认送达”，点击确认才显示“已送达”。
- [ ] 重复确认被拒绝，`delivered_at` 不变，不重复写业务送达记录。
- [ ] 重启 Java 后订单、轨迹、报告仍能查询。
- [ ] 查看者能看订单和轨迹；POST 创建/调度/送达均被服务器拒绝。
- [ ] 设置 1 分钟期限后等期限过期再调度：拒绝启动。

在 `ruoyi/frontend` 目录执行新组件类型检查和构建：

```powershell
node ../../frontend/node_modules/vue-tsc/bin/vue-tsc.js --noEmit -p tsconfig.sky.json
npm.cmd run build
```

原基础验证脚本曾允许普通无人机执行物流；新增“只用货运机”规则后，需要同步修改对应测试资源选择，不能把旧脚本失败直接当成新规则错误。不要为了让旧测试通过删掉业务规则。

### 1.13 再加两项完善，然后接入大屏

1. 订单详情显示期限和是否逾期。未完成任务用服务器当前时间判断；已完成任务用服务端完成时间判断，避免前端时钟误差。先显示逾期提示，再考虑定时产生一次性逾期告警。
2. 增加订单级取消接口。在同一事务中锁订单并调用已有 `taskAction(...,"cancel",...)`，记录取消原因。失败/取消从任务显示，不允许它们被确认送达。
3. 原大屏先做“物流订单”列表，按 `taskId` 跳转任务和地图。需要即时业务推送时，将订单列表加入 `SkyService.snapshot`，同步扩展 `shared/sky.ts` 的 Snapshot 和 emptySnapshot。不要只改前端类型、不改 Java 快照。

---

## 第二课：环境监测——从巡检任务到图片证据

### 2.1 数据与页面

新增 `st_inspection_media`：`id, task_id, file_path, captured_at, longitude, latitude, source, created_by`。

新增 `st_detection`：`id, media_id, label, confidence, bbox_json, model_version, status, reviewed_by, review_reason, created_time`。

`task_id`、`media_id` 必须有外键。影像一对多识别结果；事件还要能反查是哪张图、哪个识别结果触发。通过下一版本 SQL 给现有 `st_event` 增加可空 `detection_id`，给 `st_report` 增加可空证据引用；不要删除现有报告。

管理页组件：`InspectionWorkspace` 组合 `ImageUploadForm`、`DetectionReviewList`、`EvidenceReportPreview`。表单 emit 上传请求；列表 emit 复核；容器负责接口和错误。

### 2.2 按这个顺序逐项完成

1. 从已有环境任务选择 `taskId`，检查 type 为 `environment`。
2. 先复用现有 `/common/upload` 上传图片。该接口返回文件信息在响应根部，包括 `fileName`、`url`，不同于大部分业务接口的 `data`。
3. 新写 `POST /sky/inspection/media`，把上传后的相对文件路径、任务和拍摄位置保存。后端限制在已配置的上传目录中，并确认文件存在，不能直接接受任意磁盘路径或外网 URL。
4. 新写 `GET /sky/inspection/tasks/{id}/media`，页面显示缩略图；此时还不接模型。
5. 新写 `POST /sky/inspection/media/{id}/analyze`。第一步可以保存人工标注/演示识别结果，但 `source` 必须明确是 `manual` 或 `demo`；不能标为模型推理。
6. 真正识别再接 Python 服务：Java 发影像标识/可访问的受控路径，Python 返回类别、置信度、框和模型版本。Java 保存结果，设置处理中/成功/失败状态，并阻止重复任务产生重复结果。
7. 写 `POST /sky/inspection/detections/{id}/review`，要求 `decision=confirmed/rejected` 和原因；只有确认的异常才创建关联 `st_event`。
8. 增加报告生成或更新接口，包含原图、框、位置、拍摄时间、识别来源、复核人和建议。
9. 在大屏“应急处理”中，点击事件显示对应证据及报告。

识别结果 DTO 思考填空：

```text
confidence 范围是 ____ 到 ____。
bbox 用 ____ 坐标（像素或 0~1 归一化，选一种并写在接口说明里）。
longitude/latitude 是拍摄位置，不一定是 ____ 的精确位置。
重复点击同一张图“分析”，不应重复生成 ____。
```

参考已有上传控制器相对位置：
`ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/web/controller/common/CommonController.java`。

### 2.3 验收

- [ ] 一条环境任务上传两张图，刷新/重启后仍能查看。
- [ ] 图有文件、任务、位置、拍摄时间；不凭空生成真实坐标。
- [ ] 识别结果有来源和模型版本；人工/示例结果明确标识。
- [ ] 确认异常后只生成一个带证据的事件；驳回不会生成事件。
- [ ] 报告能从事件回到图片证据；模型失败有错误状态并可重试。
- [ ] 没有操作权限不能上传、分析或复核。

---

## 第三课：应急救援——事件驱动多条任务

### 3.1 数据与组件

新增 `st_rescue_case`：`id,title,longitude,latitude,severity,status,reported_by,created_time,closed_by,closed_time`。

新增 `st_rescue_task`：`case_id,task_id,purpose`，`purpose=scout/supply`，使用任务外键和联合唯一键。

新增 `st_rescue_action`：`id,case_id,action,result,actor,created_time`，保存现场处置，不用任务动画代替人工救援结果。

组件：`RescueWorkspace` + `RescueCaseForm` + `RescueTaskList` + `RescueTimeline`。

### 3.2 步骤

1. `POST /sky/rescue/cases` 上报事件；坐标范围、等级和标题在 Java 校验。
2. `GET /sky/rescue/cases` 和 `GET /sky/rescue/cases/{id}` 做列表/详情。
3. 上报位置必须关联一个可用降落/观测站点。第一版手动选择站点；后续再做临时站点创建，不直接把任务站点字段塞成任意坐标。
4. `POST /sky/rescue/cases/{id}/tasks` 分别创建侦察和物资投送任务，用关联表挂到同一事件。
5. 侦察选择普通无人机，投送选择满足载重的货运无人机；在服务端按 `purpose` 校验，不能只限制下拉框。
6. 给 `st_task` 添加 `priority`，所有旧任务默认普通优先级。若做待调度队列，人工或自动调度读取队列时按优先级选择；仅改 `runningTasks` 排序不会自动抢占或优先派机。
7. 无可用飞行器时显示“等待资源”，不绕过已有占用检查。本课先不做飞行中抢占。
8. `POST /sky/rescue/cases/{id}/actions` 记录人员到场、物资接收、现场结果和原因。
9. `POST /sky/rescue/cases/{id}/close` 校验必要任务已结束且有人工处置结果；仍有执行任务时要求先处理任务，再归档。
10. 把这些操作写入业务审计。大屏事件详情展示时间线和可用资源。

练习：仿照物流 `create` 写“上报事件 + 侦察任务 + 关联关系”，填写 `@____`，保证中途失败时全部回滚。自动创建侦察还是稍后创建，由你确定并写在页面提示里。

### 3.3 验收

- [ ] 一个事件能关联侦察和投送两条任务，且资源不能重复占用。
- [ ] 严重事件在待调度列表优先，但不干扰已经飞行的任务。
- [ ] 飞行完成后，事件仍需人工处置记录才能归档。
- [ ] 刷新/重启后，能查看上报人、派机原因、任务轨迹和处置人。

---

## 第四课：空中通勤——班次和座位，重点学并发事务

### 4.1 表和页面

新增 `st_commute_route`：`id,name,start_station_id,end_station_id,enabled`。

新增 `st_commute_trip`：`id,route_id,aircraft_id,task_id,departure_at,status,seat_capacity,booked_seats,delay_reason`。

新增 `st_commute_booking`：`id,trip_id,passenger_name,seats,status,created_by,created_time`。

起终点必须为 `vertiport`，飞行器必须为 `evtol`。班次容量不能超过飞行器座位数。

组件：`CommuteWorkspace` + `RouteEditor` + `TripEditor` + `BookingForm` + `BookingTable`。

### 4.2 步骤

1. `POST/GET /sky/commute/routes` 配置并查询两个起降场间的航线。
2. 为 `st_station` 增加起降场容量字段，明确是“同一时间起降占用数”，不是座位数。
3. `POST/GET /sky/commute/trips` 设置航线、eVTOL、出发时间和座位容量。
4. `POST /sky/commute/trips/{id}/bookings` 建预约；只允许未关闭预约的班次，座位数必须正数。
5. 在事务中对班次行 `SELECT ... FOR UPDATE`，检查 `booked_seats + 本次数量 <= seat_capacity`，插预约并更新已订数。
6. 取消预约也锁同一班次，只允许有效预约扣减一次，且起飞后不允许取消座位。
7. 发班次时，锁班次并关闭预约，检查已订人数大于零，再生成 **一条** `commute` 任务；人数来自数据库预约，不能相信网页传来的总人数。
8. 在调用任务分配/启动前，以固定站点 ID 顺序锁起终起降场，检查容量并写起降时间窗口预约。容量规则和并发锁必须由服务器执行；本课可以先采用保守规则：整个仿真飞行期间占用起终两个场地，完成/取消/失败后释放。后续再改为真实起降时间窗口。
9. 统一任务页面也要执行同一通勤容量检查，避免绕过新班次接口；为占用记录关联 `task_id`，重启后按数据库恢复，不能只放内存计数器。
10. 延误时保存 `delay_reason` 和新预计时间；已经执行的班次不允许随意改出发时间。
11. 状态展示从班次 + 关联任务读取；任务完成后预约才显示“已到达”。

并发关键逻辑填空（放到服务事务内，不是前端）：

```java
var trip = db.one("SELECT * FROM st_commute_trip WHERE id=? __ROW_LOCK__", tripId);
int booked = ((Number) trip.get("bookedSeats")).intValue();
int capacity = ((Number) trip.get("seatCapacity")).intValue();
if (booked + seats > capacity) throw new ServiceException("剩余座位不足", 409);
// 随后写预约，并更新 booked_seats；两条写入处于同一事务。
```

### 4.3 验收

- [ ] 4 座班次同时收到两个 3 座预约，只能成功一个。
- [ ] 重复取消预约不重复归还座位。
- [ ] 班次起飞后不能新增预约；起降场已达容量时不能再放行。
- [ ] 预约能反查班次、任务、轨迹和最终到达状态。
- [ ] 正常、延误、取消均有可理解的页面状态和原因。

---

## 第五课：空域智能管控——先有服务器校验，再有地图效果

### 5.1 先统一坐标和航线

当前仿真只有站点间直线。要做绕行，必须新增 `st_task_waypoint`：`task_id,sequence,longitude,latitude,altitude`，保存有序航点，并同时修改预计耗时、位置插值、轨迹和地图画线。只改 Three.js 中的曲线不能改变真实仿真路线。

第一版用现有 WGS84 坐标和统一的模拟高度基准。明确高度相对哪里测量；没有地形海拔数据时不能声称已经完成真实离地高度监管。

### 5.2 新增区域与冲突记录

`st_airspace_zone`：`id,name,type,polygon_json,min_altitude,max_altitude,starts_at,ends_at,enabled`。

区域类型：`no_fly` 禁飞、`height_limit` 限高、`corridor` 推荐/允许走廊。必须把走廊的约束定义写清楚，不只是画一个发光方框。

`st_airspace_conflict`：`id,task_a_id,task_b_id,zone_id,type,status,detail,created_time,resolved_by,resolution`。区域违规或两机冲突只需填相关引用，重复扫描同一未解决冲突不能无限新增记录。

组件：`AirspaceWorkspace` + `ZoneEditor` + `RouteValidator` + `ConflictList`；大屏地图只渲染后端保存的区域、航点和检查结果。

### 5.3 先做最小算法，顺序不能跳

1. `POST/GET /sky/airspace/zones` 保存并查询区域。初版表单输入矩形角点，再升级地图点选多边形。
2. 多边形至少三个不同顶点，不能自相交；检查高度上下限及生效时间。
3. 提取纯 Java 几何函数：点在多边形内、线段与区域相交、路径与高度区间相交。坐标换算成局部米制坐标再计算距离；不能把经纬度“度数”当米。
4. `POST /sky/airspace/validate` 提交候选航点和预计起飞时间，返回违规段、区域和原因。不通过时允许保存草案，但不能执行。
5. 飞行放行的统一入口 `SkyService.taskAction(...,"start",...)` 也必须检查；修改区域后重新检查待飞任务，不能相信之前网页显示过“通过”。
6. 把已有及候选任务转成同一墙钟时间轴上的预测轨迹，计算起飞、巡航、降落。预约班次时间与现有立即启动任务也要转换到同一时间轴；要考虑现有仿真的 10 倍时间和分阶段位置。
7. 同一时间比较两机水平距离与高度差。教学阈值可先设水平 30 m、垂直 10 m，但标为演示参数；这不是现实监管标准。采样之间还要做线段最近距离，避免只查整数秒漏掉交叉。
8. 放行检查和登记在同一事务内串行化：初版可用一条数据库调度锁记录 `FOR UPDATE`，避免两架机同时检查时互相看不到对方、随后一起通过。
9. 不通过时保存冲突/告警，拒绝启动；提供推迟起飞或修改航点后重新检查。
10. 调整路线时禁止前端随意改执行中任务。先只允许修改待飞草案；飞行中遇到新区域的第一版处置规则要明确，例如停止仿真并记事件，不能声称已经做到安全自主绕飞。

一个阈值判断练习：

```text
如果同一预测时刻 horizontalDistance < ____ 米
并且 abs(altitudeA - altitudeB) < ____ 米
则记录预测冲突；服务器 ____ 起飞。
```

### 5.4 必须做的验收

- [ ] 同一条航线穿过禁飞区时被服务器拒绝；绕开的航线可通过。
- [ ] 仅在某时间段生效的区域，对起飞时间调整有不同结果。
- [ ] 两架飞机相向飞过同一点同一高度时触发冲突；拉开时间后解除。
- [ ] 并发点击两架机启动，仍只有不冲突的任务通过。
- [ ] 地图与服务器使用同一批区域、航点和高度数据。
- [ ] 违规原因、调整方案、操作者和最终结果都有记录。

---

## 填空答案：先尝试，再对照

第一课笔记：`1`；`cargo`；`Java 服务端`；`人工`；`拒绝`。

第一课代码：

```text
__TASK_TYPE__       → logistics
__AIRCRAFT_TYPE__   → cargo
__ASSIGN_ACTION__   → assign
__START_ACTION__    → start
__COMPLETED_STATE__ → completed
__ENABLED__         → enabled
__CREATE_EVENT__    → create
__CREATE_FUNCTION__ → createOrder
__ALLOW_DELIVER__   → completed
```

第二课：`0`；`1`；统一坐标约定；`目标`；`识别结果/事件`。

第三课：`Transactional`。

第四课：`__ROW_LOCK__ → FOR UPDATE`。

第五课：`30`；`10`；`拒绝`，且这些只是课程演示值。

## 建议的每次学习记录

每完成一小步，记录四句话：

```text
这一步新增了什么：____
浏览器 → 控制器 → 服务 → 数据库怎么传递数据：____
失败时如何确保数据不乱：____
我用什么操作确认它有效：____
```

遇到报错时给我：做到了哪一节、对应源文件、完整错误文本。可以贴具体代码和错误，不要贴数据库密码或登录令牌。下一轮就能针对这一小步指导，而不是重写所有模块。
