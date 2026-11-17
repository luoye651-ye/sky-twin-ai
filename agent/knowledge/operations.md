# SkyTwin 操作规程与设备约束

本文仅说明本项目软件实现，不是法规、飞行许可或设备厂商性能认证。版本：2026-11-15。

## 上传图片分析与人工发现

在环境发现选择“上传检测 / 发现与处置”。上传PNG/JPEG且不超过2MiB，宽高不超过4096，总像素不超过1200万。可先点击“分析这张图片”，使用已发布漂浮物模型运行实际推理。当前类别是garbage和bottle，显示阈值0.25，置信度不是识别准确率。选择检测框后仍须声明影像来源、采集时间、WGS84位置，关联执行中或已完成的环境巡检任务，提交等待人工复核。没有检出也不证明没有漂浮物，可人工补框。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/VisionAnalysisService.java；ai/scripts/vision_upload.py；frontend/src/components/environment/DiscoveryForm.vue。

## 模型分析与事件追溯

分析记录保存输入图片SHA256、模型版本、原始预测框和置信度；发现记录保存人工选择或补充的框，二者分别保留。服务端拒绝未完成分析、图片不匹配、其他账号的分析和已关联的分析重复生成发现。发现pending_review时人工确认才生成事件，驳回不生成事件。HAIDA离线巡逻仍是独立演示，不自动推断杭州位置，不会自动创建真实城市事件；用户上传流程中的位置也只是用户声明。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/EnvironmentService.java；ruoyi/backend/sql/sky_twin_v10_vision.sql。

## 无人机电量载重与仿真边界

drone是巡检无人机、cargo是货运无人机、evtol是通勤飞行器。当前登记电量、载重和座位需实时调用工具查询，知识库不保存某架飞机的当前值。分配要求任务待分配、飞机空闲；机型、载重、座位、站点、电量、空域等仍由Java服务校验。当前预计耗电按每仿真秒0.08个百分点计算，不是实机续航模型。不能仅凭剩余电量或最大载重认定任务一定能执行。外部仿真定位终端启用时不能同时派仿真任务。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/DispatchOptimizer.java；ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/SkyService.java。

## 调度预览失败与恢复

网页生成方案需要sky:operate权限，查看需要sky:read。方案有效期5分钟。预览仅保存方案和审计，点击确认才分配；确认时重新检查任务/资源和航线版本，失败时整批事务回滚。方案过期、已确认、资源被占用或航线改变时重新生成，不绕过检查。网络中断后先查看算法调度历史和当前任务状态，再决定操作；不能看到聊天“成功”就认定已派机。分配后仍需要在任务管理执行仿真。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/DispatchService.java；frontend/src/composables/useFleetDispatch.ts。

## 连续对话与地图联动

当前会话保留最近三轮，20分钟无活动后过期，仅在当前服务内存中保存，重启后消失。按平台账号、登录身份和会话UUID隔离；清空会话或重新登录会开始新会话。历史用于理解“刚才那批任务”，不证明当前状态或本轮规则依据，必须重新查工具或检索。用户可说“定位这架飞机”或从方案卡查看航线。地图显示本地数字孪生与仿真位置，模型范围外位置不能冒充场内位置；地图操作不移动飞机。

实现依据：agent/conversation_store.py；agent/aircraft_agent.py；frontend/src/components/agent/AgentContextMap.vue。

## AI服务故障排查

助手未就绪时检查本机Agent服务、已发布模型和本地知识索引。代码或知识文档变化时旧索引会拒绝服务，需核对后运行rag_cli.py build，再重启Agent。不要发送密钥或平台令牌给模型。模型不可用时仍可在算法调度页手动预览与确认，人工发现入口也可保留人工标注。Python计算只输出结果，由Java保存业务状态；识别失败不能伪造成功框或事件。

实现依据：agent/chat_service.py；agent/rag.py；frontend/src/components/dispatch/FleetDispatchWorkspace.vue。

## 失败任务重试与待处理提醒

业务运营中心按全库分页筛选任务，提醒配送期限已过、待分配超过30分钟、待执行超过10分钟或执行状态超过60秒未更新。提醒不自动判定失败。失败或取消任务的重试创建关联新任务，原任务和轨迹不变，同一原任务最多一个活动重试。物流创建新订单并使用明确的新期限；环境侦察复用原事件处置重试。通勤班次任务必须通过班次取消/另建处理，不直接复制预约。重试不会自动分配或起飞。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/TaskOperationsService.java。

## 资源充电维护与站点容量

业务运营中心可记录仿真充电、维护停用、故障停用，需要sky:manage权限。充电/维护仅空闲飞机可开始；故障停用会在同一事务中终止占用任务并记录故障，不能同时继续飞行。结束运维恢复空闲；充电值不得低于原电量，维护/故障恢复保留原电量。起降场容量采用全航程保守占用，未配置默认200兼容旧仿真；降低容量不得破坏当前占用或已预约未来班次。不是物理充电、真实设备维修或起降场能力认证。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/ResourceOperationsService.java；ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/OperationsRules.java。

## 通勤班次预约与取消

仿真通勤班次需要两个不同且启用的eVTOL起降场，可售1～20座，时间为当前至未来30天。预约在服务端锁定班次计算余座，不允许并发超卖；只记录账号和座位数，不收集身份证或支付。锁定名单时按已确认座位生成原通勤任务，之后不再订座；仍需人工分配飞机和执行。起飞窗口为计划出发前5分钟至后15分钟。改时有版本检查，执行中/结束后不能改时；取消未起飞班次会取消任务和预约，已执行/已完成不能当作未起飞取消。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/CommuteService.java。

## 历史业务查询与报告草稿

Agent可用query_business分页查询历史任务、事件、报告，使用read_business_record读取指定任务/事件/报告证据，每问最多3次实际查询。报告中心先创建任务或环境发现的服务端快照和SHA256，再手工编辑或点击生成AI草稿；模型不能保存或审核。人工保存为新版本，审核时校验快照是否变化，审核后不可修改，原版本保留。TXT及打印版HTML导出使用已保存版本，HTML可在浏览器另存PDF。AI草稿需调用外部模型并发送所选证据，未点击不会自动发送。

实现依据：agent/dispatch_tools.py；ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/OperationsReportService.java；ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/OperationsController.java。

## 自动候选绕行与保存

航线规划页可生成候选绕行。对最多30个启用矩形禁飞/限高区域构建可见图，保留原中间必经航点，最多24个中间点，保守避开全部启用区域。建议会经过原空域、航程、电量和时限校验，但不自动保存；用户审查再保存新版本，起飞仍复查。没有建筑/地形净空、动态改线、实机避碰或真实空域审批能力，找不到路线时应明确失败。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/DetourPlanner.java；ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/RouteService.java。

## 可恢复分析运行中心

AI工作台按平台账号保存运行和成功检查点，流程为读取证据、检索规则、只读Agent分析、等待审查。重新启动后进行中的运行标为中断，用户重新登录并授权后可恢复；可能重复未完成的只读模型请求，不自动付费重试。分析阶段没有生成方案、分配、起飞或结案工具。用户明确选择1～20个任务后才单独调用Java预览；预览响应不确定时必须核对调度历史并关联真实方案编号，不能自动重发。确认分配继续使用原Java方案卡，运行中心从Java读取实际确认状态。

实现依据：agent/workbench_service.py；agent/workbench_api.py；agent/workbench_store.py。

## 我的领域知识库与图像追问

AI工作台支持账号隔离的TXT、Markdown、DOCX、文字PDF知识导入，每份不超过2MiB、正文10万字符、250片段，每账号最多20份。解析和向量化在本地进行，版本更新立即停用旧版，失败不沿用旧规则；删除后不参与新检索，旧运行的证据快照仍保留。真实分析需明确允许检索证据向外部模型发送。检测历史可跳转图像追问，点击框或选择两份分析进行比较；回答只基于Java预测框、标签、置信度、阈值和版本，不是视觉大模型直接看图，不推断拍摄地点，也不能证明目标已清理。

实现依据：agent/workbench_knowledge.py；agent/aircraft_agent.py；agent/workbench_api.py。

## 调用轨迹成本与效果评测

工作台记录实际模型和工具调用、白名单参数摘要、查询摘要哈希、耗时、失败及供应方上报的Token，不保存隐藏思维链、原始提示和凭证。未上报用量不按零计算；费用只有在运营者配置每百万输入/输出Token单价且用量完整时估算。每账号24小时最多30次运行、60次模型调用尝试。固定16条开发回归用例可比较语义/混合检索，或用户授权后比较直接模型回答与RAG只读工具；可选服务端第二模型及结构化提示词。检索命中、词语和工具断言不是事实正确率，安全与拒答样例需人工复核。

实现依据：agent/workbench_trace.py；agent/workbench_service.py；agent/workbench_cases.json。

## 地图框选与独立演示环境

AI工作台坐标示意图支持拖动框选，Java查询起点或终点站位于矩形内的待分配任务，总数来自全库，最多展示前100项。明确选择最多20项并授权才发送给Agent分析。绕行对比展示原航线和候选的距离、仿真耗时及约束，仍需人工填写原因保存，执行前重查。独立演示可用deploy/start-demo.ps1启动，使用单独账号、Cookie和AI记录库，完全禁止外部模型调用与Java业务请求，只展示合成样例和本地知识/检索；不能当作真实推理或业务闭环验收，也未自动发布公网。

实现依据：agent/demo_service.py；deploy/demo-server.mjs；agent/workbench_api.py；ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/OperationsController.java。

## DeepSeek直接看图对话

原自然语言助手勾选“图片＋自然语言”后，可上传PNG/JPEG并问“有哪些疑似漂浮物”“重点看左下角”。沿用现有DeepSeek Flash与同一API密钥，实际发送图片字节，不是读取YOLO结果冒充视觉理解。每轮先确认图片可外发；会产生API费用。回答显示候选观察、相对位置、不确定性及图片哈希，不输出虚构的精确置信度，不自动生成事件或执行任务。需要定量框时仍用原YOLO上传检测。图像会话按账号、令牌和UUID隔离，保留最近三轮，20分钟过期，换图清空历史；重启需重新传图。失败、截断或不支持图片的模型不会显示成功，不自动重试。工作台中基于已有YOLO分析记录的追问仍是结构化证据模式，与这里直接读取图片的方式不同。

实现依据：agent/vision_chat.py；frontend/src/composables/useImageChat.ts。
