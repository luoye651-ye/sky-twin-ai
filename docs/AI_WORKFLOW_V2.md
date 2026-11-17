# 视觉业务接入、知识问答和连续对话第一版

日期：2026-11-07，Asia/Shanghai。用户授权直接实现，并选择先完成代码与隔离验证；未要求代操作现有业务。

## 使用入口

1. 环境发现 `/environment` 顶部新增“上传检测 / 发现与处置”，地址 `/environment?mode=evidence`。旧离线巡逻和历史discoveryId深链接保留。
2. 选择执行中/已完成的环境巡检任务，上传≤2MiB PNG/JPEG。点击“分析这张图片”，等待实际YOLO预测，选择最多20个框，或者改用人工补框；图像、位置、来源、时间由用户核对后提交。
3. 提交的发现为待人工复核，人工确认后才生成事件。原始分析ID、图片哈希、模型版本和预测框独立保留，人工框另存。沿用原事件、应急侦察、后图与归档流程。
4. 应急侦察任务待分配时，可点“为此任务生成AI方案”，只预填问题、不自动发送。方案卡中“查看航线”打开对话地图。
5. Agent指挥页支持连续对话。例如先为物流任务生成普通方案，再说“把刚才那批任务改成紧急，只生成预览”。历史中的真实对象ID保留，但每轮重新查询状态，确认仍由人工点击。
6. 查询飞机后可说“在地图上定位这架飞机”。模型地图工具只返回已查询的对象ID；地图从Java快照/航线接口读取实际数据，不接受模型编造的经纬度。
7. 知识问答的“查看回答依据”展开本轮检索片段、文件、行号和文档版本，可核对回答。引用存在不等于已自动证明每句话正确。

## 组件和状态归属

| 层 | 职责 |
| --- | --- |
| VisionAnalysisService | Java持久化上传分析状态、图证、模型指纹，限定进程和输出校验 |
| vision_upload.py | 固定已发布模型对单张图计算；支持CUDA/CPU，不写业务库，不要求完整训练集 |
| EnvironmentService | 验证分析所属人/完成态/图像哈希/未绑定，事务关联发现；人工复核才生成事件 |
| VisionAnalysisPanel | 管理单图分析及人工框选择；通过事件把分析和框交给DiscoveryForm |
| DiscoveryForm | 组合任务、来源、位置、时间、图片及人工框，提交原有发现接口 |
| ConversationStore | 当前进程内、按账号+令牌哈希+会话UUID隔离最近三轮历史，20分钟TTL、200会话上限 |
| chat_service | 新鲜鉴权、会话上下文、并发与请求重放；不接受客户端自行提交历史或系统角色 |
| aircraft_agent | 历史辅助理解指代、本轮重新调用工具；地图定位仅输出查询过的ID |
| AgentConversation / AgentDispatchCard | 展示对话、来源与方案，向上发出定位事件 |
| AgentContextMap | 从当前Java数据读取飞机/任务航线，复用CityViewport；加载完成后定位 |

Java仍是业务状态唯一拥有者，没有在FastAPI创建第二套任务/事件状态。SQL `sky_twin_v10_vision.sql`仅增加分析证据表，迁移已加入原脚本。

## 规则与运行边界

- 原始图片SHA256、模型SHA256、分析ID、图像尺寸、阈值、类别、框坐标和置信度由Java校验。只接受garbage/bottle、阈值0.25、最多100个原始预测；发现表最多20个人工确认框。
- Python进程使用固定脚本和生成的UUID目录，不使用上传文件名作为路径，不接受任意命令/模型路径，最长120秒；与离线巡逻共用计算文件锁，避免并行争用。失败不生成事件。
- 同时最多一个上传分析处于running。相同requestId/图片/用户重放返回原记录，其他内容拒绝；服务重启将未完成分析标为失败，不伪装完成。
- 分析与事件不是同一件事。HAIDA测试图不包含可信杭州定位，不能从图片推断杭州现场坐标；上传定位仍为用户声明。YOLO置信度不是准确率。
- 当前推理权重沿用原模型，没有在本轮训练或宣称精度提升。处置后图与现实清理效果仍由人工提供，不由模型自动结案。
- 连续对话历史只在服务内存中保存，清空时客户端更换会话UUID；退出/重新登录按身份隔离，重启后丢失。无长期记忆或跨用户共享。旧引用不能充当本轮依据。
- 知识库扩为4份白名单文件、20段。新增操作规程、模型追溯、仿真设备约束、调度恢复和会话说明；检索采用语义相关性门槛内的关键词/语义排名融合，门槛不因测试结果下调。

## 本轮验证证据

- Python Agent/RAG/聊天/会话/地图隔离回归71项通过；真实LangChain循环、模拟模型与HTTP数据，不冒充真实模型答题效果。
- 前端类型检查与生产构建通过；7项流协议检查包含地图对象类型、ID及引用长度拒绝。保留原有第三方注释/大包警告。
- Java全模块编译及打包通过（打包命令跳过自动测试；下面的验收为独立运行）。
- 19项Java计算输出/证据绑定规则检查通过。
- 16项真实Java/MySQL隔离检查通过：在3307唯一临时库应用原环境表及新迁移，实际调用Java服务并启用真实事务；覆盖图证绑定、待复核态、人工生成单个事件、幂等、跨账号/重复分析拒绝、晚期失败回滚。临时库在finally删除，不写现有业务库记录。
- 两项Python框归一化单测通过；一张HAIDA test离线图实际运行已发布YOLO上传计算链，检出1个，CUDA0。证据 `docs/verification/vision-upload-model.json`，结果保留在其中analysis_id对应的 `ai/runs/vision/`。不是杭州图像或真实业务事件。
- 原20条检索回归、新增8条功能覆盖用例均通过，见 `rag-retrieval.json` 和 `knowledge-extension.json`。这是检索覆盖，不是28个独立研究样本或大模型准确率。
- 自动审批拒绝真实RAG模型验收：理由为将本地项目知识片段发给外部DeepSeek未经本轮明确授权。本轮未绕过拒绝，未执行 `verify_assistant_workflows.py --paid-model`；该脚本只在后续获得明确授权后使用。
- 用户选择先代码与隔离验证，未正常登录执行本轮新功能。因此尚未完成真实账号网页“上传→分析→复核→事件”、连续对话真实模型效果和地图完整交互验收，不把编译/隔离测试当作已完成这些验收。

本机加载新代码前只读确认执行中任务与活动巡逻均为0；仅新增分析表、构建并加载受管Java/Agent，没有创建、分配、执行或结案现有任务，没有操作3306/6379。

## 复验

Agent目录：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest test_dispatch_tools test_conversation test_chat_service test_rag_agent test_aircraft_agent test_rag -q
.\.venv\Scripts\python.exe -X utf8 rag_cli.py build
.\.venv\Scripts\python.exe -X utf8 rag_evaluate.py
.\.venv\Scripts\python.exe -X utf8 verify_knowledge_extension.py
```

AI目录（本地模型，不发外部API）：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s scripts -p test_vision_upload.py -v
.\.venv\Scripts\python.exe -X utf8 scripts/verify_vision_upload.py
```

Java独立检查源码：`VisionAnalysisChecks.java`、`VisionWorkflowChecks.java`。本轮classpath参数文件在 `tmp/assistant-integration-checks/`；参数文件采用正斜杠避免Windows反斜杠被Java当作转义。

下一小步学习：选择一张图，用分析ID→发现ID→事件ID解释服务端关联；再解释为何“模型检出”与“人工确认事件”是两个状态。不因本轮生成代码而标记用户掌握。
