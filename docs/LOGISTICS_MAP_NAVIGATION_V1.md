# 物流任务地图跟踪第一版

## 使用

在物流运输列表点击「地图跟踪」，或在配送详情点击数字孪生跟踪链接，进入 `/digital-twin?taskId=任务编号`。直接进入数字孪生时会自动选中一项执行中的物流任务；没有执行任务时可以手动选择。任务编号写入 URL，刷新后保留；完成后不会悄悄切换到其他任务。

地图中青色为计划航线，绿色为 Java 已保存的飞行轨迹，黄色为剩余路线，白色点和方向箭头表示所选任务的位置及后续方向。支持查看完整航线、定位任务位置及物流任务切换。起终点由地图标记和面板站点名称共同展示。

## 数据流与规则

1. Java `FlightRoutes.attach` 读取任务冻结的航线版本和 `elapsed_seconds`，用 `FlightNavigation` 生成 `Task.navigation`；与仿真器共用 `RouteEngine.at` 插值，不创建第二套任务状态，不新增表。
2. `navigation.position` 是本任务对应仿真时刻的位置，不取飞行器复用后执行其他任务的位置。`remainingRouteMeters` 是从当前位置沿全部后续航点到终点的水平球面距离；`destinationDistanceMeters` 是当前位置到终点的水平大圆距离。均用 WGS84 经纬度计算，不用 Three.js 投影或可视化抬升高度计距。
3. 距离随现有 Java SSE 快照更新；前端只读展示，不通过浏览器时钟自行推进任务。`remainingSimulationSeconds` 是仿真剩余时间，不是实机预计到达时间，第一版不在面板展示。
4. 已飞轨迹通过既有 `GET /sky/tasks/{id}/tracks` 每 3 秒读取，只画服务端保存点；不把计划航线前半段伪装成实际轨迹。切换任务/离开页面取消请求并忽略过期结果；请求串行，不累积重叠轮询。
5. 上升阶段水平剩余距离可保持不变；下降阶段水平距离可为 0，但仍是执行中。只有 Java 确认降落才显示完成。完成飞行不自动确认物流送达；取消/失败显示停止处位置与剩余航程，不再推进。
6. SSE 中断显示数据暂停；轨迹请求失败显示警告，旧轨迹可能滞后。缺少导航字段显示不可用，不编造数值；超出城市范围不伪造场内位置或连接跨范围历史段。
7. 沿用 `sky:read` 和现有统一业务权限，无派机、起飞、订单状态或 AI 模型写请求。本模块是本地仿真导航展示，不是实机遥测、真实自动驾驶或飞行导航设备。

## 组件职责与学习提纲

- `FlightNavigation.java`：服务端纯计算，可独立测试；计算规则不依赖页面。
- `useFlightNavigation.ts`：从 Pinia 读快照、从 URL 读所选任务、轮询历史轨迹；不修改业务对象。
- `FlightNavigationPanel.vue`：props 输入数据，emit 选择任务和相机操作事件。
- `flightNavigationOverlay.ts`：只把导航数据转换为 Three.js 线和标记。
- `DigitalTwinWorkspace.vue`：组合面板、地图和数据逻辑，路由页保持轻量。

可选小练习：解释为什么绕行时“沿航线剩余”大于“距终点直线”，以及为什么距离为 0 不一定代表任务完成。代码已生成/测试不代表用户已掌握这些规则。

## 验证

```powershell
# 项目根目录：真实服务端接口验收，会创建并清理唯一前缀测试数据。
python ruoyi/scripts/verify-navigation.py

# 前端目录：纯函数/绘图与既有航线、定位回放回归。
npm run verify:navigation
npm run verify:routes
npm run verify:positioning
npm run build

# 项目根目录：Java 纯计算检查（先完成 backend 编译）。
& './ruoyi/.runtime/jdk-17.0.20.1+1/bin/java.exe' -cp 'ruoyi/backend/ruoyi-admin/target/test-classes;ruoyi/backend/ruoyi-admin/target/classes' com.ruoyi.skytwin.FlightNavigationChecks
```

浏览器检查脚本 `frontend/scripts/verify-navigation-ui.mjs` 需要 Playwright，可通过 `SKYTWIN_PLAYWRIGHT_MODULE` 指定已安装包位置。不新增 npm 依赖。浏览器使用明确的隔离样例账号/API，但加载真实地图和 UAV 资源；截图不代表真实任务现场证据。真实 Java/MySQL/SSE 的验证另存 `docs/verification/navigation-api.json`；界面验证在 `navigation-ui.json`，截图 `navigation-desktop.png`、`navigation-mobile.png`。

本次只部署 Java 导航读模型和大屏展示，无数据库迁移、无需新模型或 API Key；未修改原任务/订单/航线业务规则。测试清理仅删除本轮唯一前缀的临时资源，系统操作日志保留。

实际验收记录：Java 导航纯计算149项断言及另外6组已有业务计算检查通过；前端全部44项测试、类型检查和生产构建通过。真实接口15项、隔离浏览器14项通过。真实测试绕行航程约1399.89m逐步减至0，测试资源残留计数均为0。构建仍有原有大分包提示，不宣称已完成全站性能优化。
