# SkyTwin AI
# AI Native Low-altitude Economy Digital Twin Platform

版本：v1.0
用途：
1. 中国研究生智慧城市技术与创意设计大赛参赛项目
2. AI 全栈工程岗位作品
3. 后续论文、软著、求职项目基础

---

# 1. 项目背景

## 1.1 项目定位

SkyTwin AI 是一个面向智慧城市低空经济场景的 AI Native 数字孪生智能管控平台。

通过：

- 数字孪生
- 无人机智能感知
- 大语言模型 Agent
- MCP 工具调用
- RAG 知识库
- AI 工作流
- 空天地数据融合

实现：

无人机任务管理、
城市低空监管、
异常事件分析、
智能巡检、
自动报告生成。


---

# 2. 项目核心展示场景

## 场景一：无人机智能巡检

用户：

"帮我巡检A区域"

Agent 自动：

1. 理解任务
2. 查询区域信息
3. 调用无人机调度工具
4. 规划航线
5. 更新数字孪生地图
6. 分析检测结果
7. 自动生成报告


---

## 场景二：低空数字孪生城市

展示：

- 三维城市
- 无人机模型
- 飞行轨迹
- 实时位置
- 空域状态
- 环境数据


---

## 场景三：AI智能控制台

用户自然语言：

"最近有没有无人机异常?"

Agent:

调用：

- 数据库查询
- 视频检测服务
- 历史日志
- 知识库

返回：

智能分析结果。


---

# 3. 总体技术架构


                    用户

                     |
                     |

              Vue3 Web平台

                     |

 ------------------------------------------------

 |                    |                          |

数字孪生模块        AI Agent控制台        数据中心


                     |

              FastAPI Backend


                     |

 ------------------------------------------------

 |              |              |

Agent服务     业务服务       数据服务


                     |

 ------------------------------------------------


LLM:
DeepSeek API


Agent Framework:

LangChain

LangGraph


工具调用:

MCP


知识库:

RAG


数据库:

PostgreSQL

Redis


文件:

MinIO


部署:

Docker


---

# 4. 前端架构


## 技术栈

必须：

Vue3

TypeScript

Vite

Pinia

Vue Router


可视化：

CesiumJS

Three.js

ECharts


UI:

Element Plus


---

# 5. 前端功能模块


## 5.1 数字孪生大屏


目录:

src/views/DigitalTwin


功能：

- 城市三维地图
- 无人机模型
- 飞行路径动画
- 空域区域显示
- 实时数据


技术：

Cesium:

负责：

- 地球
- 城市地图
- GIS


Three.js:

负责：

- 无人机模型
- 动画
- 特效


---

## 5.2 AI Agent控制台


页面：

src/views/AgentConsole


功能：

类似 ChatGPT 控制台。


支持：

用户输入：

"分析最近一次巡检"


Agent返回：

- 思考过程
- 工具调用
- 结果


---

## 5.3 数据分析页面


包含：

- 飞行统计
- 异常数量
- 巡检结果
- AI分析


使用：

ECharts


---

# 6. 后端架构


技术：

Python

FastAPI


目录:


backend/

├── api

├── services

├── agent

├── models

├── database

├── utils


---

# 7. 后端核心模块


## 7.1 用户服务

功能：

用户认证

权限管理


---

## 7.2 无人机管理服务


功能：

无人机：

- 注册
- 状态
- 位置
- 任务


接口:

GET /api/drone/list

POST /api/drone/task


---

## 7.3 数字孪生服务


负责：

三维数据

空间数据

实时状态


---

# 8. AI Agent架构


## 技术


LangChain:

负责：

- LLM调用
- Prompt管理
- Tool管理


LangGraph:

负责：

复杂工作流。


例如：


用户任务

↓

任务理解节点

↓

任务规划节点

↓

工具调用节点

↓

结果分析节点

↓

报告生成节点



---

# 9. MCP工具体系


设计：

mcp_server/


工具：


## drone_tool


无人机控制


例如：

start_mission()


get_position()



---

## database_tool


查询数据库


例如：

query_history()


---

## detection_tool


调用视觉模型


例如：

detect_object()


---

## report_tool


生成报告


例如：

generate_report()



---

# 10. RAG知识库


目的：

让Agent理解低空领域知识。


知识：

- 无人机规范
- 城市管理条例
- 飞行安全规则
- 应急方案


技术：

Embedding

Vector Database


推荐：

Milvus

或者

Chroma


流程：

文档

↓

Embedding

↓

向量数据库

↓

Retriever

↓

Agent


---

# 11. 计算机视觉模块


结合已有论文。


模块：

vision_service


输入：

无人机图片/视频


输出：

目标检测结果


支持：

YOLO系列


接口：

POST

/api/detection


返回：

{

objects:[],

confidence:0.95

}



---

# 12. 数据库设计


PostgreSQL


核心表：


## drone


无人机信息


字段：

id

name

location

status



---

## mission


任务


字段：

id

drone_id

route

status



---

## detection_result


检测结果


字段：

image

object

confidence



---

## agent_history


AI对话记录



---

# 13. 项目目录结构


SkyTwin-AI/


frontend/

 backend/


 mcp-server/


 ai-agent/


 vision-service/


 docker/


 docs/


 README.md


---

# 14. 工程化要求


必须包含：


Docker Compose


Nginx


日志系统


环境变量管理


Git规范


API文档


自动测试


---

# 15. AI Native开发规范


开发流程：

需求

↓

Spec文档

↓

Cursor生成代码

↓

人工Review

↓

测试

↓

提交


所有功能必须先写：

feature_spec.md


---

# 16. 开发阶段规划


## Phase 1

基础Demo


完成：

Vue框架

三维地图

无人机模型

基础后台


目标：

可以展示。


---

## Phase 2

AI能力


加入：

DeepSeek

LangChain

Agent


实现：

自然语言控制系统。


---

## Phase 3


MCP + LangGraph


实现：

复杂任务自动执行。


---

## Phase 4


企业级优化


加入：

Docker

权限

日志

监控


---

# 17. 比赛展示流程


开场：

智慧城市低空痛点


展示：

三维城市


输入：

"执行A区域巡检"


Agent规划


无人机飞行


检测异常


生成报告


结束：

AI赋能低空经济。


---

# 18. 求职能力映射


对应岗位：


中控技术：

√ 企业平台

√ AI Agent

√ 全栈开发

√ 工程规范


阿里云：

√ AI Web产品

√ LLM应用

√ Prompt工程

√ 数据可视化


网易：

√ Vue3

√ Vite

√ 前后端闭环

√ AI辅助开发



---

# 最终目标

打造：

一个具备：

AI Agent能力

数字孪生能力

全栈工程能力

低空行业场景

的大型AI Native应用系统。

# 19. 第一阶段 Demo 详细设计

## 19.1 Phase 1 目标

不追求功能完整，只追求"能跑起来、能看见、能汇报"：

- 前端能启动，展示一个三维场景（城市占位 + 无人机模型 + 简单飞行动画）
- 后端能启动，提供无人机列表 / 下发任务的 mock 接口
- 前端能通过接口拿到后端数据并渲染出来（打通全栈链路）
- 不接数据库、不接大模型、不接真实 GIS 数据，全部先用内存 mock 数据

Phase 1 不用 Cesium，先用 Three.js 搭一个"简化城市"（地面网格 + 几个方块楼 + 一个无人机模型沿固定航线飞）。
原因：Cesium 需要申请 Ion Token、加载真实地形/影像，属于"锦上添花"，Phase 1.5 再接入，避免一开始就卡在申请 Key、调地图底座上。

## 19.2 Phase 1 页面原型（文字线框）

```
┌─────────────────────────────────────────────┐
│  SkyTwin AI   [数字孪生] [AI控制台*]          │  ← 顶部导航（*占位，Phase2 开放）
├───────────────┬───────────────────────────────┤
│ 无人机列表      │                               │
│ ┌───────────┐ │        3D 场景                │
│ │ 🚁 D-01 巡检中│         （地面网格+建筑方块     │
│ │ 🚁 D-02 空闲  │          +无人机沿航线飞行）    │
│ │ 🚁 D-03 空闲  │                               │
│ └───────────┘ │                               │
│ [下发巡检任务]  │                               │
└───────────────┴───────────────────────────────┘
```

交互：

1. 页面加载 → 调用 `GET /api/drone/list` → 左侧渲染无人机卡片
2. 点击"下发巡检任务" → 调用 `POST /api/drone/task` → 3D 场景中对应无人机沿返回的 route 飞行
3. 无人机状态（idle / flying / returning）用不同颜色区分

## 19.3 Phase 1 API 设计

| 方法 | 路径 | 说明 | 请求体 | 返回 |
|------|------|------|--------|------|
| GET | `/api/drone/list` | 获取无人机列表 | - | `[{id, name, location:{lat,lng,alt}, status}]` |
| POST | `/api/drone/task` | 下发巡检任务（mock 规划航线） | `{drone_id, area}` | `{mission_id, drone_id, route:[{lat,lng,alt}], status}` |
| GET | `/api/health` | 健康检查 | - | `{status:"ok"}` |

Phase 1 全部使用内存字典存储，不落库；字段名与第 12 节数据库设计保持一致，方便 Phase 4 直接迁移到 PostgreSQL。

## 19.4 数据库 ER 图（提前设计，Phase 1 暂不接入）

```
drone (无人机)                mission (任务)              detection_result (检测结果)
┌───────────────┐            ┌───────────────┐          ┌───────────────────┐
│ id         PK │◄──────┐    │ id         PK │          │ id             PK │
│ name           │       └────┤ drone_id   FK │◄────┐    │ mission_id     FK │
│ location(json) │            │ route(json)   │      └────┤ image              │
│ status         │            │ status        │          │ object             │
└───────────────┘            │ created_at    │          │ confidence         │
                              └───────────────┘          └───────────────────┘

agent_history (AI对话记录)
┌───────────────┐
│ id         PK │
│ session_id     │
│ role (user/ai) │
│ content        │
│ created_at     │
└───────────────┘
```

关系：`drone 1 --- N mission`，`mission 1 --- N detection_result`。

## 19.5 LangGraph 工作流预览（Phase 2 实现）

```
用户输入 "帮我巡检A区域"
        ↓
   [任务理解节点]  解析出 区域=A, 意图=巡检
        ↓
   [任务规划节点]  选择空闲无人机 + 规划航线
        ↓
   [工具调用节点]  调用 MCP drone_tool.start_mission()
        ↓
   [结果分析节点]  调用 detection_tool 分析巡检图像
        ↓
   [报告生成节点]  调用 report_tool 生成结构化报告
        ↓
   返回给前端 AgentConsole（展示思考过程 + 工具调用 + 最终结果）
```

## 19.6 MCP 工具定义预览（Phase 3 实现）

Phase 1/2 先在后端用普通函数模拟这些工具的行为，Phase 3 再拆成独立 MCP Server：

```python
# drone_tool
start_mission(drone_id: str, area: str) -> Mission
get_position(drone_id: str) -> Location

# database_tool
query_history(filter: dict) -> list[Mission]

# detection_tool
detect_object(image_url: str) -> DetectionResult

# report_tool
generate_report(mission_id: str) -> str  # markdown 报告
```

## 19.7 Cursor 开发 Prompt 模板（配合第 15 节 AI Native 开发规范）

每写一个新功能前，先在对话里给 Cursor 这样的结构化 Prompt（对应 OpenSpec/SDD 范式）：

```
【背景】参考 docs/PROJECT_SPEC.md 第 X 节
【目标】实现 xxx 功能
【范围】只改动 frontend/src/views/DigitalTwin 下的文件，不要动其他模块
【验收标准】
1. npm run dev 能正常启动，无报错
2. 页面能展示 xxx
3. 不引入新的第三方依赖（如需引入需先说明）
【禁止】不要一次性生成整个项目，只完成本次范围内的代码
```

## 19.8 岗位能力映射细化（对照 docs/profile.md）

| profile.md 中的要求 | 本项目对应模块 | 所处阶段 |
|---|---|---|
| React/Vue + Node/Java/Go/Python 全栈 | Vue3 前端 + FastAPI 后端 | Phase 1 |
| ChatGPT/Cursor/Copilot AI 提效、Prompt Engineering | 全程用 Cursor + 结构化 Spec Prompt 开发（19.7） | 全程 |
| LLM 应用、RAG、Agent 智能体、AI 工作流 | AI Agent 控制台 + LangChain/LangGraph + RAG 知识库（8/10节） | Phase 2/3 |
| LangChain/LlamaIndex | LangChain 负责 LLM 调用与工具管理（8节） | Phase 2 |
| Agentic 编程工具 + OpenSpec/SDD 开发范式 | 第 15 节 AI Native 开发规范、19.7 Prompt 模板 | 全程 |
| Vue3+Vite 复杂页面架构、组件封装、状态管理、性能优化 | 数字孪生大屏 + Pinia 状态管理（4/5节） | Phase 1/4 |
| Go 轻量级 BFF / 业务接口 | 可选扩展：用 Go 重写/新增一个 BFF 层做接口聚合（见下方"可选加分项"） | Phase 4（可选） |
| 低代码/DevOps/研发效能 | Docker Compose、Nginx、日志、自动测试（14节） | Phase 4 |
| 计算机视觉 / 目标检测 | vision_service + YOLO 检测（11节） | Phase 3 |
| 问题拆解、系统架构能力 | 本 Spec 本身 + 分阶段开发过程 | 全程 |

**可选加分项（面向网易岗位的 Go BFF）**：Phase 4 阶段可以新增 `bff/`（Go + Gin），职责是聚合 FastAPI 后端接口、做轻量鉴权与数据裁剪，前端只对接 BFF。这一模块非必须，视时间和简历侧重取舍。

---

# 赛题基本描述
本赛题聚焦智慧城市低空领域发展难题，推动空天技术与城市治理深度融合。参赛队伍可围绕无人机、eVTOL、卫星遥感、空天地一体化网络等方向创作，覆盖城市物流配送、空中通勤、环境监测、应急救援、空域智能管控等应用场景。作品需结合北斗定位、数字孪生、人工智能集群调度等核心技术，解决低空监管缺失、飞行器安全、空天数据利用不足等城市痛点。评审综合考量技术创新性、方案落地性、创意设计与产业价值，鼓励兼顾民生服务与产业发展，打造适配现代智慧城市、兼具工程实践与社会价值的低空经济综合解决方案。


# 指导
要求不要一下子就生成所有代码，要教会我一点点从0开始搭建这个项目