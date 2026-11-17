# 低空业务基础能力

2026-10-19环境增量：在同一Java业务源上完成河道漂浮物图证人工复核、应急侦察任务、处置后图片及不可变归档闭环。见`ENVIRONMENT_RESPONSE_V1.md`；当前未配置视觉模型，不是AI识别或实机救援，原有通用告警、物流、飞行与安全规则保留。

2026-10-19多机增量：已在同一Java业务源上增加起飞前时空冲突检查、错峰预约/取消、到点复查自动起飞及持久化统一仿真时钟。详见`MULTI_AIRCRAFT_TRAFFIC_V1.md`；不是实机避障或运行安全认证，旧文中的未实现描述需按此增量理解。

2026-10-19增量：物流闭环、约束优化集群调度、禁飞/限高起飞校验、定位接入仿真与回放，以及人工多航点规划已在同一Java业务服务上接入。多航点边界/验证见 `WAYPOINT_ROUTES_V1.md`。下面“本轮范围”及2026-10-10验证记录保留为初始基础阶段，不代表最新功能缺口。

业务数据的唯一归属为 `ruoyi/backend` 的 Java 服务及专用 MySQL。原 `backend/` 的 FastAPI Demo 保留；本轮不再通过它执行飞行任务，后续 Agent 通过鉴权接口调用 Java。

## 本轮范围

1. 飞行器与五类站点的维护，资源被占用时禁止修改；移除保留历史。
2. 配送、通勤、环境监测、应急救援、空域巡查五类任务；新建 → 分配 → 执行 → 完成 / 取消 / 失败。五类场景共用基础流程，专属订单、乘客预约、视觉识别、空域规则仍属后续阶段。
3. Java 定时仿真允许多机执行，事务内保存位置、速度、电量、任务进度、轨迹、告警、摘要报告及审计。完成由服务端确认，不由动画判断。
4. JWT + `sky:read` / `sky:operate` / `sky:manage`；超级管理员可全部操作，调度员执行任务与处置事件，查看者只读。新增角色不默认授权给现有账号。
5. 鉴权 SSE，每两秒推送状态快照。连接每20秒结束并重连，重连时重新校验权限与令牌；撤销权限后需重新登录刷新若依缓存权限。登录令牌不放进 URL。

SSE 的初始 HTTP 请求仍经过 JWT 与方法权限校验；仅允许容器对 `/sky/stream` 的内部 ASYNC 收尾分派，避免连接到期时重复鉴权阻断响应关闭。相关机制见 [Spring Security 分派类型与请求授权文档](https://docs.spring.io/spring-security/reference/servlet/authorization/authorize-http-requests.html#match-by-dispatcher-type)。
6. 保存的数据在重启后可查询；执行中的任务在重启后按保存进度继续仿真，停机期间不虚构轨迹。

## Vue 组件与数据流

- 管理端 `SkyWorkspace`：组合筛选栏、列表、编辑表单与任务操作对话框。
- `ResourceEditor`：接收资源种类与待编辑记录，提交合法输入。
- `TaskEditor`：接收站点数组，提交五类任务配置。
- `BusinessTable`：接收列、记录、允许的操作，以事件上报选择与操作。
- `TaskActionDialog`：接收任务、飞行器、操作类型，提交分配信息和原因。
- `useSkyWorkspace`：负责管理端请求、实时订阅及错误反馈。
- 大屏 `useSkyStore`：只保存服务端快照和登录状态；负责鉴权、流的重连及清理。
- `CityViewport`：接收飞行器、站点和任务；展示三维场景，位置取自服务器。
- `FleetPanel`：接收资源与连接状态，展示实时遥测。
- 大屏任务、报告、事件页面组合上述业务展示组件，通过 Java API 操作。

## 数据与仿真边界

`st_aircraft / st_station / st_task / st_track / st_event / st_report / st_audit` 七张表。演示坐标为 WGS84，经纬度转换到三维本地坐标；不代表已经接入北斗设备。

飞行仿真是起飞、直线巡航、降落，10倍演示时间，最少20秒；不是实机飞控、避障算法或真实空域审批。资源跨站点起飞按仿真方式设置起点，尚不包含调机航程。告警来源于仿真低电量与任务失败，报告为系统任务摘要，不能冒充 AI 影像识别报告。

业务列表默认最近500条；单任务轨迹最多2000点。实际大规模运行还需分页、归档、可靠消息和多实例调度锁。本地单Java进程部署适用。

## 启动与学习入口

新增数据库迁移：`powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\migrate-sky.ps1`，仅操作专用3307数据库，可重复执行。

Java 核心代码：`ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/`。从 `SkyController.createTask` → `SkyInputs.Task` → `SkyService.createTask` → `SkyRepository` 看一次创建流程，再看 `SkyService.tick` 中同一事务如何同时更新任务、资源和轨迹。

## 验证记录（2026-10-10）

集成脚本验证六机并发、五类任务完成、两个线程争用一个资源、匿名/查看者/调度员权限、CRUD与输入校验、鉴权SSE、电量及任务失败告警、事件处置、轨迹与报告及操作记录。重启Java两次，分别验证执行中恢复和结束后的历史查询。测试不依赖浏览器动画，测试资源在 finally 中按本次返回的唯一编号清理。日志为 `ruoyi/logs/foundation-verification.log`。

额外验证长连接：`verify-live.py` 通过5173的 Java 代理读取两个完整生命周期的 SSE，接收到11及12个快照，连接到期正常关闭并可重新鉴权连接，匿名初始请求仍被拒绝。两端类型检查与构建、Java多模块打包均通过。浏览器验证了大屏登录页面加载和控制台无错误；登录后的全部按钮操作以接口验收与类型检查覆盖，尚未逐个做浏览器操作验收。
