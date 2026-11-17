# SkyTwin AI 从 0 搭建任务清单

配合 `docs/PROJECT_SPEC.md` 使用。原则：**每次只做一小步，跑起来、看得见效果，再进入下一步**。
每个任务后面标注了"验收标准"，做完自己勾一下 `[x]`，方便复盘进度。

---

## Phase 0：环境准备（必须先做）

- [ ] **0.1 修复 Node.js 环境（重要，已发现的真实问题）**

  排查发现你电脑上全局的 `npm`/`npx` 来自一个 **2019 年的 Node.js v11.9.0**
  （安装在 `C:\Nodejs-v11.9.0`），而 Vite / Vue3 这类现代前端工具链要求
  **Node.js 18 及以上**。用旧 npm 装依赖会直接报错
  （`Invalid dependency type requested: alias`），无法安装成功。

  **修复步骤**：
  1. 去 [nodejs.org](https://nodejs.org) 下载并安装 **Node.js 22.x LTS**（Windows Installer）
  2. 安装完成后重新打开终端，执行 `node -v`，确认输出 `v22.x.x`
  3. 执行 `npm -v`，确认输出 `10.x` 以上（新版 Node 自带的 npm）
  4. 如果 `npm -v` 还是显示旧版本，说明 PATH 里 `C:\Nodejs-v11.9.0` 排在新 Node 前面，
     打开"系统环境变量" → 编辑 `Path`，把新安装的 Node 目录（一般是
     `C:\Program Files\nodejs`）移到 `C:\Nodejs-v11.9.0` 之前，或者直接删掉旧目录的 Path 条目

  验收标准：`node -v` ≥ 18，`npm -v` ≥ 9，且只有一个 Node 安装在生效。

- [ ] **0.2 确认 Python 环境**（这一步在本机已验证可用：Python 3.13）

  验收标准：`python --version` 输出 3.10 及以上。

---

## Phase 1：基础 Demo（打通全栈链路）

> 本阶段代码已经写好在仓库里（`frontend/`、`backend/`），你要做的是**看懂 + 跑起来 + 改一改**，
> 而不是重新写一遍。

### 1.1 后端跑起来

- [ ] 打开 `backend/` 目录，创建虚拟环境：`python -m venv .venv`
- [ ] 激活虚拟环境并安装依赖：
  ```powershell
  .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```
- [ ] 启动服务：`python -m uvicorn app.main:app --reload --port 8000`
- [ ] 浏览器打开 `http://127.0.0.1:8000/docs`，能看到 Swagger 接口文档

  验收标准：能在 Swagger 页面里手动调用 `GET /api/drone/list`，返回 3 台 mock 无人机数据。

- [ ] **走读代码**（建议阅读顺序，边看边理解，不用改）：
  1. `backend/app/models/schemas.py` —— 数据结构长什么样
  2. `backend/app/services/drone_service.py` —— mock 数据和"下发任务"的假逻辑
  3. `backend/app/api/drone.py` —— 接口是怎么暴露出去的
  4. `backend/app/main.py` —— FastAPI 应用是怎么组装起来的（路由 + CORS）

### 1.2 前端跑起来（需先完成 Phase 0.1）

- [ ] 进入 `frontend/` 目录，安装依赖：`npm install`
- [ ] 启动开发服务器：`npm run dev`
- [ ] 浏览器打开终端提示的地址（通常是 `http://localhost:5173`）

  验收标准：
  1. 页面顶部能看到"数字孪生 / AI控制台"导航
  2. 中间是深色 3D 场景：地面网格 + 几栋方块楼 + 3 个彩色圆锥（无人机）
  3. 左侧能看到无人机卡片列表（说明前端成功从后端拿到了数据）
  4. 点击某张卡片的"下发巡检任务"，对应的圆锥会沿一个矩形航线飞一圈

  如果第 3、4 步失败，检查 `backend` 是否还在运行（前端通过 `vite.config.ts` 里的
  proxy 把 `/api` 请求转发到 `http://127.0.0.1:8000`）。

- [ ] **走读代码**（建议阅读顺序）：
  1. `frontend/src/types/drone.ts` —— 前端的数据类型定义
  2. `frontend/src/api/drone.ts` —— 怎么调用后端接口
  3. `frontend/src/stores/drone.ts` —— Pinia 状态管理，页面数据从哪来
  4. `frontend/src/views/DigitalTwin/useCityScene.ts` —— Three.js 场景怎么搭的（建筑、无人机、动画）
  5. `frontend/src/views/DigitalTwin/index.vue` —— 页面怎么把 store 和 3D 场景粘在一起

### 1.3 自己动手改一点点（巩固理解，不追求难度）

- [ ] 在 `drone_service.py` 里再加一台无人机 `D-04`，重启后端，看前端是否自动多出一张卡片
- [ ] 把 `useCityScene.ts` 里 `buildingLayout` 数组加一栋楼，观察 3D 场景变化
- [ ] 把无人机颜色 `droneColors` 改一下，验证状态变化时颜色确实会变

### 1.4 Git 初始化

- [ ] `git init`，确认 `frontend/.gitignore`、`backend/.gitignore` 生效（`node_modules`、`.venv` 不进仓库）
- [ ] 第一次提交：`git add . && git commit -m "phase1: 基础数字孪生demo"`

---

## Phase 2：接入 AI 能力（自然语言控制）

> 目标：能在 AI 控制台里输入"帮我巡检A区域"，由大模型理解意图并调用 Phase 1 已有的接口。

- [ ] 2.1 申请 DeepSeek API Key，在 `backend/.env` 里配置（先手动测试一次 API 能否调通）
- [ ] 2.2 后端新增 `app/agent/llm.py`：封装一个最简单的"调用 DeepSeek，返回文本"的函数
- [ ] 2.3 后端新增 `app/agent/simple_agent.py`：用 LangChain 把"用户输入" → "调用 drone_service.dispatch_mission" 串起来（先不用 LangGraph，用最简单的 function calling 或规则匹配即可跑通）
- [ ] 2.4 新增接口 `POST /api/agent/chat`，输入 `{message}`，返回 `{reply, tool_calls}`
- [ ] 2.5 前端把 `views/AgentConsole/index.vue` 从占位页改成真正的聊天界面（输入框 + 消息列表）
- [ ] 2.6 联调：输入"帮我巡检A区域" → 页面显示 Agent 思考过程 → 3D 场景里无人机真的飞起来

  验收标准：全程不用手动点无人机卡片，纯靠自然语言就能触发 Phase 1 的飞行动画。

---

## Phase 3：LangGraph + MCP（复杂任务自动执行）

- [ ] 3.1 把 Phase 2 的"简单 Agent"重构成 LangGraph 状态图（参考 `PROJECT_SPEC.md` 19.5 节的 5 个节点）
- [ ] 3.2 独立出 `mcp-server/` 项目，把 `drone_tool`、`database_tool` 实现为标准 MCP 工具
- [ ] 3.3 新增 `vision-service/`，跑通一个最小的 YOLO 目标检测接口（先用现成预训练模型 + 示例图片）
- [ ] 3.4 把 `detection_tool`、`report_tool` 接入 LangGraph 工作流，实现"巡检 → 检测异常 → 自动生成报告"全链路
- [ ] 3.5 搭建 RAG 知识库（Chroma），灌入无人机规范/应急方案等文档，Agent 能引用知识库回答问题

---

## Phase 4：工程化收尾（企业级 / 求职作品打磨）

- [ ] 4.1 引入 PostgreSQL，把 Phase 1 的内存 mock 数据迁移成真实表（对照 `PROJECT_SPEC.md` 第 12 节 ER 图）
- [ ] 4.2 引入 Redis（缓存 / 会话）
- [ ] 4.3 编写 `docker-compose.yml`，一键启动 frontend/backend/db/redis
- [ ] 4.4 加 Nginx 反向代理配置
- [ ] 4.5 补自动化测试：后端至少覆盖 `drone_service` 和核心接口；前端至少覆盖关键组件
- [ ] 4.6 加日志系统、统一异常处理、环境变量管理规范
- [ ] 4.7（可选，对齐网易岗位）用 Go + Gin 写一个轻量 BFF，聚合 FastAPI 接口
- [ ] 4.8 补全 README、架构图、演示视频/截图，作为求职作品和比赛展示材料

---

## 复盘习惯建议

每完成一个 Phase，花 10 分钟写一段简短复盘（可以直接写在这个文件底部）：

- 这个阶段我真正理解了什么？
- 哪里是让 Cursor 生成的，我看懂了吗？能不能自己口述一遍逻辑？
- 下个阶段最大的风险/不确定点是什么？

<!-- 复盘记录从这里往下追加 -->
