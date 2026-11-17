# SkyTwin AI 新人入门

这份文档只讲当前仓库已经实现的内容。先把 Phase 1 Demo 跑通，再考虑 AI、数据库和部署；`PROJECT_SPEC.md` 里提到的 LangChain、MCP、RAG、PostgreSQL 等，目前属于后续设计。

## 1. 先建立整体认识

SkyTwin AI 当前是一条很短的全栈链路：

```text
浏览器
  ↓
Vue 页面 → Pinia 状态 → Axios API
  ↓                 ↓
Three.js 3D 场景    Vite 代理 /api
                    ↓
              FastAPI :8000
                    ↓
              内存 Mock 数据
```

用户打开“数字孪生”页面后，前端请求 `GET /api/drone/list`，后端返回 3 台无人机。点击“下发巡检任务”后，前端请求 `POST /api/drone/task`，后端生成一条矩形航线，前端让对应的 Three.js 无人机沿航线飞行。

## 2. 从零安装并启动

需要：Node.js 18+、npm、Python 3.10+。建议使用 Node.js 22 LTS。

### 启动后端

打开终端一：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

验证：打开 <http://127.0.0.1:8000/docs>，调用 `GET /api/drone/list`；也可以打开 <http://127.0.0.1:8000/api/health>。

### 启动前端

打开终端二：

```powershell
cd frontend
npm install
npm run dev
```

打开终端输出的地址，通常是 <http://localhost:5173>。

前端请求使用相对路径 `/api`，由 `frontend/vite.config.ts` 转发到后端 `http://127.0.0.1:8000`。因此开发时必须同时运行两个终端。

## 3. 建议的源码阅读顺序

### 后端：从数据到接口

- `backend/requirements.txt`：后端依赖，当前只有 FastAPI、Uvicorn、Pydantic。
- `backend/app/main.py`：创建 FastAPI 应用，配置 CORS，挂载路由，并提供健康检查。
- `backend/app/models/schemas.py`：定义 API 输入输出的数据结构；它相当于前后端共同遵守的“数据合同”。
- `backend/app/services/drone_service.py`：业务逻辑和内存数据。`_drones` 是假数据，`dispatch_mission` 生成矩形航线并把无人机状态改成 `flying`。
- `backend/app/api/drone.py`：HTTP 层，只负责接收请求、调用 service、把异常转换成 HTTP 错误。
- `backend/app/agent/`、`database/`、`utils/`：目录已经预留，但当前没有实际功能。

调用关系是：

```text
GET /api/drone/list
  → api/drone.py:get_drone_list
  → drone_service.list_drones
  → _drones
```

### 前端：从启动到交互

- `frontend/package.json`：依赖和脚本；`dev` 开发、`build` 类型检查并打包、`preview` 预览生产包。
- `frontend/index.html`：浏览器入口，提供 `#app` 挂载点。
- `frontend/src/main.ts`：创建 Vue 应用，安装 Pinia、路由、Element Plus 和全局样式。
- `frontend/src/App.vue`：全局布局、顶部导航、路由出口 `RouterView`。
- `frontend/src/router/index.ts`：定义 `/digital-twin` 和 `/agent-console` 两个页面路由。
- `frontend/src/types/drone.ts`：前端 TypeScript 类型，与后端 Pydantic 模型对应。
- `frontend/src/api/drone.ts`：Axios 请求封装，不负责页面状态。
- `frontend/src/stores/drone.ts`：Pinia 状态中心，保存无人机列表、当前任务和加载状态。
- `frontend/src/views/DigitalTwin/index.vue`：数字孪生页面，负责按钮、列表、生命周期和 API/3D 场景的协调。
- `frontend/src/views/DigitalTwin/useCityScene.ts`：纯 Three.js 场景模块，创建地面、建筑、无人机，处理动画、缩放和销毁。
- `frontend/src/views/AgentConsole/index.vue`：当前只是 Phase 2 占位页。
- `frontend/src/style.css`：全局基础样式。
- `frontend/vite.config.ts`：Vite 配置和 `/api` 开发代理。
- `frontend/tsconfig*.json`、`*.d.ts`：TypeScript 编译检查配置和 Vue/Vite 类型声明。

### 文档与其他文件

- `docs/PROJECT_SPEC.md`：完整产品愿景、架构设计、数据表和 Phase 规划；很多内容尚未实现。
- `docs/TASKS.md`：从环境准备到 Phase 4 的分步任务清单。
- `docs/profile.md`：项目对应的岗位能力要求，属于背景材料。
- `kylin-om-agent-software-manual-revised.docx`：外部参考资料，不参与程序运行。
- 各目录的 `__init__.py`：让 Python 将目录识别为包；目前多数为空，是为后续模块扩展预留的。
- `package-lock.json`：根目录遗留的空 npm lock；真正的前端依赖锁文件是 `frontend/package-lock.json`。

## 4. 第一次动手练习

按下面顺序改动，每次改完刷新页面或重启服务：

1. 在 `drone_service.py` 的 `_drones` 中增加 `D-04`，观察左侧是否多一张卡片。
2. 在 `useCityScene.ts` 的 `buildingLayout` 中增加一栋楼。
3. 修改 `droneColors`，观察不同状态的无人机颜色。
4. 在 Swagger 中调用任务接口，再回到页面理解“接口返回数据”和“3D 动画”是两件事。

## 5. 常见问题

- 页面没有无人机：确认后端运行在 8000 端口，并直接访问 `/api/drone/list`。
- PowerShell 不允许运行 `npm.ps1`：使用 `npm.cmd install` 或 `npm.cmd run dev`，或者调整 PowerShell 执行策略。
- Node 版本过低：先检查 `node -v`，低于 18 就升级；旧 Node 常导致依赖安装失败。
- 任务按钮报错：后端必须保持运行；任务接口只接受已有的无人机 ID。
- 重启后端数据恢复原样：这是内存 Mock 的正常行为，当前没有数据库。

## 6. 后续搭建路线

1. Phase 1：理解并稳定当前链路，补测试和错误提示。
2. Phase 2：新增 `/api/agent/chat`，先用简单规则或函数调用打通自然语言巡检。
3. Phase 3：再引入 LangGraph、MCP、视觉检测和 RAG。
4. Phase 4：最后接 PostgreSQL、Redis、Docker、日志、监控和自动化测试。

每次只完成一条能验证的链路：先定义数据结构，再写后端接口，再接前端 API，最后接页面交互。
