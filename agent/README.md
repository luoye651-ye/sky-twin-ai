> 2026-11-15：原对话新增[DeepSeek实际看图](../docs/DEEPSEEK_IMAGE_CHAT.md)，只复用现有服务。上传图片后可自然语言提问并继续追问，结果与YOLO框明确区分。110项Python隔离回归通过；经用户单次授权，真实合成图看图通过，未测实际漂浮物准确率。项目知识4份30段。

> 2026-11-14增量：[AI工程工作台](../docs/AI_ENGINEERING_WORKBENCH.md)加入持久化可恢复分析、实际工具/模型轨迹、用量与费用、领域知识导入/版本、检索及Agent对照、图像证据追问、空间交互和独立演示。项目知识4份29段，上传资料按账号隔离。100项Python隔离回归通过；真实外部模型新链路、真实账号浏览器端到端尚未验收。独立演示见[启动说明](../deploy/README.md)。

> 2026-11-08增量：网页增加历史任务/事件/报告查询及明细、历史任务地图定位和报告草稿工具链；每轮最多3次实际业务查询，固定只读Java路径。AI草稿不保存/审核，需用户点击触发外部模型请求。[运营增量与验证边界](../docs/OPERATIONS_V1.md)。

> 2026-11-07第二次增量：现已支持最近三轮连续对话、飞机/任务地图联动、可展开的知识原文与版本；环境页可上传图片实际分析并接人工复核事件。旧文中的“每问独立/仅3份知识/只读”按[本轮说明](../docs/AI_WORKFLOW_V2.md)更新。真实账号网页端到端和外部模型新功能效果尚待验收，本轮先完成代码与隔离验证。

# 2026-11-07增量：网页自然语言调度

网页助手已支持查询待分配任务、调用Java方案预览，并在对话方案卡中人工确认分配。示例：“请为所有待分配的物流任务生成调度方案，先预览不要执行。”

预览保存方案及审计，需要sky:operate；任务和飞机仅在点击卡片确认并通过Java校验后分配，不自动起飞。最多20个任务，资源变化、过期、重复确认仍由原Java服务拒绝。CLI仍保持原只读工具范围。每条问题独立，请明确任务对象。

实现及验收见[自然语言调度说明](../docs/NATURAL_LANGUAGE_DISPATCH.md)。以下旧版说明中的“网页没有派机能力/只读”按本增量理解。

# 本地 Agent：自然语言查询与RAG知识问答

已接入LangChain工具编排、本地中文向量RAG、stdio MCP飞行器查询与网页聊天窗口。尚无自然语言派机能力。网页发送问题或运行agent_smoke.py会调用DeepSeek并消耗API额度；单元测试、rag_cli.py、rag_evaluate.py和mcp_smoke.py不调用付费大模型。不写任务状态。

网页已部署在Agent指挥页：http://127.0.0.1:5173/agent-command 。默认自然语言助手，原集群调度保留在算法调度页签；启停、鉴权和使用边界详见[WEB_CHAT.md](WEB_CHAT.md)。

## 直接运行自然语言查询

本机已经安装FastEmbed、下载并校验中文模型、构建知识索引；沿用原来的DeepSeek配置。从项目根目录执行：

```powershell
.\agent\.venv\Scripts\python.exe .\agent\agent_smoke.py
```

然后输入：`命中禁飞区后还能起飞吗？` 或 `应急事件结案需要哪些证据？`

知识问题不需要Java启动或平台令牌；仅在实际查询飞行器时才要求有效SKYTWIN_TOKEN。

也可以一次性传入问题：

```powershell
.\agent\.venv\Scripts\python.exe .\agent\agent_smoke.py --question "当前有哪些空闲的巡检无人机？分别还有多少电量？"
```

通常是两次模型请求：选择工具、读取结果后回答。混合问题可能更多；总流程90秒超时、默认图循环最多10步、每个问题最多实际调用一次MCP和3次不同知识检索，重复调用复用结果。RAG模式将本次模型客户端的输出上限设为1024 token以容纳引用，不改用户llm_client.py的原256配置；token上限不是固定消耗。加`--aircraft-only`可使用原单工具模式（6步、原模型上限，不加载知识库）。

飞机问题验收时观察工具执行/完成日志，答案中只列本次Java返回的符合条件飞机及电量。规则问题观察知识检索日志及[K1]等引用；终端会打印由程序验证过的文档、章节和行号。没有工具执行证据时不显示成功回答；检索无匹配时强制返回“没有找到依据”；伪造或缺失引用、查询失败、空回答、明确的截断元数据会报错。引用有效性不等于自动证明每句话都正确，模型仍可能误解片段，重要判断需人工核对。

## RAG的运行与维护

学习提纲：LangChain负责模型与工具循环；MCP负责用登录身份读取Java动态业务数据；RAG负责把文档分段并向量化，按问题检索片段后让模型基于证据回答。不是把整个项目塞进提示词，也不是重新训练DeepSeek。索引中的向量帮助找相关内容，引用用于追溯来源，两者都不能单独保证答案事实正确。

- `agent/knowledge/platform.md`：状态查询、任务流程、HAIDA离线巡逻与应急事件的边界。
- `agent/knowledge/airspace.md`：禁飞、限高、连续航段检查、时间边界和起飞拦截。
- `agent/knowledge/response.md`：人工证据、复核、侦察、轨迹和处置后证据的结案条件。

当前13个章节片段，最多380字符、50字符重叠；只索引这三份白名单文档，不扫描.env、日志、训练集或业务导出。引用包含文件/章节/行范围及代码依据。代码和文档指纹存入索引；改变依据后拒绝继续使用旧索引，须先审查文档再重建。索引是JSON，不读取不可信pickle。

中文Embedding使用[FastEmbed支持的BGE-small-zh-v1.5](https://qdrant.github.io/fastembed/examples/Supported_Models/)，512维，CPU ONNX；[固定Qdrant模型版本](https://huggingface.co/Qdrant/bge-small-zh-v1.5/tree/46fbe35fd4374a00fee7de77dfddaeb6dd6a2c59)，模型约94.8MB、MIT标记，下载后校验模型SHA-256。没有额外Embedding API Key，不复制PyTorch/GPU训练环境。首次公开模型下载需要网络；准备好后向量生成与检索完全本地运行，使用LangChain InMemoryVectorStore按余弦相似度检索，持久化到agent/.cache，不新增数据库服务或端口。被检索到的少量项目片段会随问题发送给DeepSeek组织回答，不把凭证发送给模型。

换电脑或从源码重新安装时：

```powershell
.\agent\.venv\Scripts\python.exe -m pip install -r .\agent\requirements.txt
.\agent\.venv\Scripts\python.exe .\agent\rag_cli.py prepare
.\agent\.venv\Scripts\python.exe .\agent\rag_cli.py build
```

修改规则文档并核对代码后，只需要重跑build。测试纯检索（不花DeepSeek额度）：

```powershell
.\agent\.venv\Scripts\python.exe .\agent\rag_cli.py search --query "应急事件结案需要哪些证据？"
.\agent\.venv\Scripts\python.exe .\agent\rag_evaluate.py
```

相似度阈值0.50在20条手写回归用例上校准；它不是概率，也不能可靠鉴别所有域外问题。20条用例复用作校准，不是独立测试集，不能宣称100%检索/回答准确率；证据在docs/verification/rag-retrieval.json。知识库仅为当前软件规则，不能当官方法律法规/飞行许可，也不存当前可飞空域清单或具体任务获准结果。

## 数据流和文件职责

`mcp_smoke.py → stdio子进程 mcp_server.py → sky_client.py → Java GET /sky/aircraft`

自然语言入口在这条链路之前增加：`agent_smoke.py → aircraft_agent.py（LangChain＋DeepSeek选择工具）`，工具返回后再由模型组织回答。

- `sky_client.py`：固定查询本机8081；携带平台身份，校验HTTP状态、AjaxResult业务码及飞行器字段；只返回允许的字段。
- `mcp_server.py`：将查询包装为唯一工具 `list_aircraft`，返回结构化结果；失败为工具错误，不伪装成空列表。
- `mcp_smoke.py`：用当前虚拟环境解释器启动子进程、发现工具、调用并退出。它不是LLM Agent，只是协议验收客户端。
- `aircraft_agent.py`：组装飞行器MCP与知识检索工具，保存本问题的调用记录并校验引用；凭证由本地代码持有，不作为模型工具参数。
- `rag.py`：受限文档分段、本地Embedding、JSON索引、源码指纹与余弦检索；`rag_cli.py`负责下载/建库/纯检索。
- `agent_smoke.py`：负责命令行输入、输出及退出状态，默认启用RAG；支持交互输入、`--question`和`--aircraft-only`。

MCP不占用新的TCP端口。不要通过是否弹出窗口判断启动成功；手动运行服务端会等待stdio输入，请用下面的客户端命令。

## 验证命令

在项目根目录 PowerShell 运行：

```powershell
.\agent\.venv\Scripts\python.exe -m pip install -r .\agent\requirements.txt
.\agent\.venv\Scripts\python.exe -m pip check
.\agent\.venv\Scripts\python.exe -m unittest discover -s agent -p 'test_*.py' -v
.\agent\.venv\Scripts\python.exe .\agent\mcp_smoke.py --check-tools
```

71项单元/协议测试使用模拟模型、Java身份和样例向量/数据，不请求DeepSeek、不用真实令牌。其中一项真实启动stdio子进程，仅将Java适配器替换为样例。另20条本地检索回归、5条前端流解析及12项隔离浏览器检查通过；截图“UI验收样例”不代表现场模型答复。测试不证明真实模型生成答案的正确率。`--check-tools`验证MCP协议，不查询Java。

## 配置平台身份并查询真实登记数据

保留原有 `agent/.env` 中的DeepSeek配置，只追加：

```dotenv
SKYTWIN_TOKEN=你当前平台登录令牌的值
```

不要填写DeepSeek密钥，不加`Bearer`前缀、不发送给助手。可在已登录平台的浏览器开发者工具中查看已有Java请求的 `Authorization` 请求头，复制 `Bearer ` 后面的值。令牌过期后需重新登录更新。环境变量中的同名配置优先于.env，包括显式空值。

Java必须在8081运行，当前平台账号需要 `sky:read` 权限，然后执行：

```powershell
.\agent\.venv\Scripts\python.exe .\agent\sky_client.py
.\agent\.venv\Scripts\python.exe .\agent\mcp_smoke.py
```

验收：两条命令的飞行器数量/编号与平台一致；MCP结果 `source=java`、`simulation=true`，工具清单仅 `list_aircraft`。Java登记数据仍为仿真系统数据，不证明实机状态。缺令牌、无权限、后端不可用必须报错，不能显示为成功的0架。

## 当前验收状态（2026-10-20）

用户已亲自运行mcp_smoke.py并提供Java真实登记数据4架的成功输出，MCP→Java只读鉴权查询已确认。启动脚本已使用集中RedisPort配置；此前6380问题的只读检查显示它落在Windows保留范围6380～6479，项目现使用16380。

用户已亲自运行真实DeepSeek飞机查询，正确从4架中筛出D-01/D-02及对应电量。RAG模型/索引及网页聊天服务已部署，上述回归通过，真实8002及5173代理健康、匿名/无效令牌拒绝亦已确认；未代发付费DeepSeek网页/RAG请求，真实生成回答与引用待用户在页面发送问题确认。

## 安全边界和下一步

令牌不作为MCP工具参数，不输出、不交给模型；子进程只显式传递平台令牌和Python运行选项，不传DeepSeek Key。服务端保持stdout只用于协议。工具的只读声明不是权限控制，真实权限仍由Java强制检查。平台返回的名称等文本只当数据，不能当指令。

CLI仍为单用户本机方式；网页已按每次登录身份隔离，不能把CLI全局平台令牌用于所有网页用户。RAG在本地LangChain工具中执行，MCP仍仅提供Java飞行器查询；没有新增MCP写工具。下一步先验收网页带来源的真实回答；派机等写操作另设确认和服务端校验。若令牌曾贴到聊天里，先退出重登使旧令牌失效，新令牌只保存在本机。
