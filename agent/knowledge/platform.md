# SkyTwin平台操作说明

## 飞行器状态和只读Agent

查询当前空闲巡检无人机、电量或运力时，必须通过list_aircraft工具，经本地MCP向Java的GET /sky/aircraft读取登记数据；知识文档不保存实时飞机数量、电量或任务状态。drone表示巡检无人机，cargo表示货运无人机，evtol表示通勤飞行器，idle表示空闲。查询要求平台登录身份及sky:read权限。数据属于仿真登记信息，不证明实机遥测；电量和载荷余量不能单独证明任务可执行。CLI保持只读。网页Agent可以生成调度预览，人工点击方案卡确认后才分配任务，不自动起飞或结案。

实现依据：agent/aircraft_agent.py；agent/mcp_server.py；ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/SkyController.java。

## 创建、分配与执行任务

任务起点和终点必须不同，站点必须启用且未删除。通勤任务需要乘客和两个eVTOL起降场；非通勤任务不能设置乘客。任务只有在created新建状态才可分配飞行器，飞行器必须idle空闲；分配时服务端检查机型、运力、仿真电量等约束。起飞前必须先分配，任务为assigned，飞行器也应为assigned；执行时重新检查调度约束、空域规则和多机起飞安全。以上是本地仿真状态机，不是向真实飞控发送指令。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/SkyService.java：createTask、taskAction、validateDispatch。

## AI水域巡逻识别演示

环境发现页面的AI巡逻使用HAIDA test影像池和已发布的YOLO检测模型，属于离线航拍影像识别演示，不是杭州实时画面或无人机实际巡航。每次新巡逻从132张影像池随机抽取1～132张，抽样数量随本次记录保存；重试、刷新或查看同次历史记录不重新抽样。新巡逻可能偶然与上次同数量。模型没有就绪时拒绝启动，不伪造检测框。列表展示逐图检出数量并可查看实际预测框图片；模型检出不等于人工确认的事件。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/PatrolEvaluationService.java：config、start、evaluate。

## 巡逻识别与应急事件的边界

AI识别漂浮物后会自动生成应急事件或派机吗？不会。离线检测与人工复核后的应急处置是分开的流程。

AI巡逻识别记录保存在st_patrol_eval，完成时记录patrol.completed审计，不自动创建应急事件、占用飞行器或改变飞行任务。人工证据闭环是另一条流程：提交发现证据、人工复核确认、安排应急侦察、人工提交处置后证据再结案。两者不能混称“检测完即自动救援”。此知识库仅解释项目规则，不是法律法规、飞行许可、真实北斗硬件或实机救援能力证明。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/PatrolEvaluationService.java；ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/EnvironmentService.java。


## 网页自然语言调度方案

网页可按明确的任务编号、标题或类型查询待分配任务和飞行器，再调用Java生成调度方案。一次最多20个任务，优先级1普通、2优先、3紧急；默认普通。任务查询只覆盖最近500条中的待分配项，不能声称全部历史。生成预览保存方案和审计，但不占用飞机、不分配任务。预览和人工确认都需要sky:operate权限；只读账号可查询。方案卡从Java重新读取，以服务端结果为准。人工审查、填写原因、点击确认后，Java复查资源/航线/电量等约束并事务分配；方案有效期5分钟，过期、重复确认或状态变化会拒绝。分配不等于起飞，需在任务管理执行仿真。当前会话保留最近三轮并可理解指代，20分钟无活动后过期；每轮重新查询状态。

实现依据：agent/dispatch_tools.py；agent/aircraft_agent.py；ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/DispatchController.java；ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/DispatchService.java。
