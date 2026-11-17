# 物流配送第一版：实现与验收

完成日期：2026-10-18。范围为 SkyTwin 平台中的本地仿真配送闭环；用户本轮明确授权助手直接完成剩余工作。

## 使用

打开 `http://127.0.0.1:5173/logistics`，刷新浏览器即可使用。

1. 新建配送订单，选择两个不同的启用站点，填写重量、时限与原因。
2. 在订单行点击“分配”，选择符合条件的空闲货运无人机。
3. 点击“执行仿真”，填写原因，Java 开始更新飞行状态。
4. 列表每3秒自动刷新。点击“查看配送”，可查询订单/关联任务/飞行器、历史轨迹、操作记录。
5. Java 完成飞行后显示“待确认送达”，填写原因确认后变为“已送达”。已结束订单不能重新调度；尚未完成的配送可以取消。

支持货物/订单编号/站点搜索、配送阶段筛选、最近200条订单的每页20条展示。统计卡同样只覆盖这最近200条；没有宣称全库分页或全量统计。轨迹提供 WGS84 航迹示意和每页20条记录，不是带底图的三维地图。

## 规则与数据流

- `st_logistics_order` 只保存订单事实 `created/delivered`；运输阶段读取关联 `st_task`，不维护第二套飞行状态机。
- 订单分配/执行/取消调用同一个 `SkyService.taskAction`。从平台、若依或原任务接口进入，均应用相同的物流规则。
- 物流必须使用 `cargo` 货运无人机。分配检查资源空闲、载重与仿真电量；起飞再次检查载重、电量和时限。
- 配送截止时间使用服务端墙钟；分配及起飞前用“当前时间 + 预计仿真秒数”检查能否按时抵达。飞行仍为原有10倍时间和简化电量模型。
- 订单事务先锁订单再锁任务；通用任务服务读取不可变的订单时限时不反向锁订单，避免相反锁顺序。送达状态、确认人、时间与业务审计在同一事务内保存。
- 只有任务 `completed` 才允许确认送达。已取消、失败、尚未完成及已送达不能重复确认。
- 创建/调度/取消/送达要求 `sky:operate`，详情/列表/轨迹要求 `sky:read`。前端隐藏不可用操作，Java 独立校验权限和业务状态。
- 列表与详情都有轮询清理、卸载后响应隔离和错误提示。操作失败保留输入；操作成功后的列表刷新失败不会误报为保存失败。

## 接口

路径前缀均为 `/sky/logistics/orders`；大屏使用 `/java-api` 代理，若依使用 `/dev-api`。

| 方法 | 相对路径 | 用途 |
|---|---|---|
| GET | `/` | 最近200条订单及任务、飞行器状态 |
| POST | `/` | 创建订单与关联任务 |
| GET | `/{id}` | 订单详情与订单/任务操作记录 |
| GET | `/{id}/tracks` | 根据订单关联关系查询轨迹 |
| POST | `/{id}/assign` | 分配货运机，输入aircraftId/reason |
| POST | `/{id}/start` | 执行仿真，输入reason |
| POST | `/{id}/cancel` | 取消配送，输入reason |
| POST | `/{id}/deliver` | 确认送达，输入reason |

若依部分失败响应HTTP仍为200，应读取JSON `code`。不以HTTP 200或动画飞完代替业务完成。

## 文件

```text
frontend/src/
  api/logistics.ts                         请求与类型
  composables/useLogisticsOrders.ts         列表、刷新队列与轮询
  composables/useLogisticsActions.ts        创建和订单操作状态
  composables/useLogisticsDetail.ts         详情/轨迹请求及生命周期
  components/logistics/
    LogisticsOrderPanel.vue                页面组合、搜索、统计
    LogisticsOrderTable.vue                列表、分页与操作事件
    LogisticsOrderForm.vue                 创建表单
    LogisticsActionDialog.vue              分配/执行/取消/送达弹窗
    LogisticsDetailDialog.vue              详情与审计
    LogisticsTrackView.vue                 航迹示意和轨迹表
    logisticsPresentation.ts               阶段/时间/超时展示
ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/
  LogisticsService.java                    订单查询及动作封装
  LogisticsController.java                 HTTP与权限
  SkyService.java                          统一物流放行规则
ruoyi/backend/sql/sky_twin_v2_logistics.sql  可重复运行的建表迁移
ruoyi/scripts/migrate-sky.ps1               新部署同时纳入物流迁移
ruoyi/frontend/src/components/sky-twin/
  TaskActionDialog.vue                     统一任务入口的货运机筛选
```

已有订单表无需重建；未改用户已有订单、站点坐标、原3306 MySQL或6379 Redis，也未给旧FastAPI增加业务状态。

## 验收证据

- Java完整Maven打包 `BUILD SUCCESS` 并已启动新服务。
- 大屏 `npm.cmd run build`：vue-tsc与Vite通过。
- 若依前端生产构建通过。
- 最终 `verify-logistics-deliver.py --ui`：59项集成检查、10项浏览器检查通过。报告 `ruoyi/logs/logistics-workflow-verification.json` 和 `logistics-ui-verification.json` 均为 `passed=true`。
- 覆盖货运类型、载重、电量、资源争抢、过期/时限不足、起飞时复查、权限、失败/取消、重复起飞、提前/重复/并发送达、审计故障事务回滚、订单详情/轨迹关联、Java重启恢复。
- 隔离浏览器实际点击创建、分配、执行、查看轨迹、确认送达，等待Java仿真完成，验证自动更新及刷新持久化；查看者可读但无创建/调度入口，页面切换无未捕获错误。
- 浏览器仅有一个补充错误用例使用局部响应拦截模拟409，以验证弹窗保留原因。正常配送链路连接真实Java/MySQL；后端真实拒绝和事务回滚另有集成验证，不将模拟响应冒充服务器业务结果。
- 测试使用独立随机站点、飞行器、订单及查看者，全部测试业务数据、资源、触发器和临时账号访问已清理，系统登录/操作日志按若依软删除习惯保留。原用户订单确认状态/确认人/时间与验收前相同。
- 最终 `check.ps1`：3307/6380/8081/5173/5174均就绪且受本项目管理，API代理和Redis健康检查通过。
- 截图：`docs/verification/logistics-delivery-detail.png`，其中订单是已清理的隔离验收数据。

运行浏览器时发现原创建表单 `min=0.01 / step=0.1 / value=1.00` 不满足HTML原生步长约束，提交事件不会触发；已将重量步长修正为0.01。实际浏览器空表单提示及正常创建均已验证。Windows重启验收脚本改为输出文件，避免后台Java继承PIPE使测试进程等待不结束；中断轮次的临时数据亦已按唯一前缀精确清理。

## 复跑

```powershell
cd D:\cursor\project\sky-twin
# 后端规则与重启恢复
D:\miniconda\python.exe .\ruoyi\scripts\verify-logistics-deliver.py --workflow
# 同时跑隔离浏览器（本机使用已安装Chrome和工作区运行时Playwright）
D:\miniconda\python.exe .\ruoyi\scripts\verify-logistics-deliver.py --ui
```

测试读取本地秘密配置但不输出密码、验证码或令牌；登录令牌只通过测试子进程环境传入隔离浏览器，不写入报告、不复用用户浏览器配置。`--ui-only`可单独重跑浏览器检查。

## 边界与学习点

这是本地仿真版，未接真实无人机、真实载荷续航、障碍物避碰或民航空域放行。用户已有6个上海演示站点与滨江地图的坐标对齐仍是独立待决事项，本轮没有迁移历史坐标，也未将轨迹示意称为滨江三维地图联调完成。剩余四类场景和Agent仍按各自计划推进。

最值得回看的数据流是：`LogisticsOrderTable.emit → useLogisticsActions → Java订单服务 → 同一任务状态机 → 列表/详情查询`。本轮助手按用户授权直接实现，不据生成代码或助手验收推断用户已经掌握这些内容。
