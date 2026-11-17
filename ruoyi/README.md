# SkyTwin RuoYi 业务管理后台（独立本地部署）

本目录包含官方 RuoYi 的 Java 后端和 Vue 3 管理前端，与你原有的 `../frontend/`（数字孪生大屏）和 `../backend/`（FastAPI）分开。

## 访问地址

| 服务 | 地址 / 端口 |
|---|---|
| RuoYi 管理前端 | http://127.0.0.1:5174 |
| RuoYi Java 后端 | http://127.0.0.1:8081 |
| 专用 MySQL | 127.0.0.1:3307，数据库 `sky_twin_ruoyi` |
| 专用 Redis | 127.0.0.1:16380 |
| 原 SkyTwin 指挥中心 | http://127.0.0.1:5173 |
| 本地只读Agent聊天服务 | http://127.0.0.1:8002，通过Agent指挥页访问 |
| 原 FastAPI | http://127.0.0.1:8000 |

本次是 Windows 本地开发部署，前端通过 Vite 开发服务器提供访问。没有配置公网域名、HTTPS 或生产环境反向代理。构建产物是 `frontend/dist/` 与 `backend/ruoyi-admin/target/ruoyi-admin.jar`。生产部署前需为 `/prod-api` 配置 Java 反向代理。

初始登录：`admin / admin123`，验证码按页面输入。后续可在个人中心修改密码。数据库、Redis、JWT 使用独立随机凭据，保存在 `config/local-secrets.json`，请勿提交。管理界面和 Java API 只监听本机。

## 目录清单

```text
ruoyi/
├── backend/                    官方 Spring Boot 3 后端，独立 Git 仓库
│   ├── ruoyi-admin/            启动入口、Controller、资源配置；target/为构建结果
│   ├── ruoyi-system/           用户、角色、菜单等 Service / Mapper / 实体
│   ├── ruoyi-framework/        Spring Security、JWT、Redis 等框架配置
│   ├── ruoyi-common/           公共类型、注解、工具
│   ├── ruoyi-generator/        CRUD 代码生成器
│   ├── ruoyi-quartz/           定时任务模块
│   ├── sql/                    官方系统表和 Quartz 初始化 SQL
│   └── pom.xml                 Maven 多模块工程入口
├── frontend/                   官方 Vue 3 管理前端，独立 Git 仓库
│   ├── src/views/sky-twin/      SkyTwin 管理首页；原官方首页仍保留
│   ├── src/views/system/       系统管理页面
│   ├── src/api/                Java API 请求代码
│   ├── src/router/             路由
│   ├── vite.config.js          固定5174，/dev-api代理到8081
│   └── dist/                   管理前端构建结果
├── config/                     本地覆盖配置，不改官方默认数据库配置
│   ├── application-sky-twin.yml 后端本地 profile；凭据从环境变量读取
│   ├── maven-settings.xml      Maven Central 镜像配置
│   ├── runtime.local.json     本机工具路径（不提交）
│   ├── local-secrets.json      随机数据库 / Redis / JWT 凭据（不提交）
│   ├── mysql.ini              专用3307实例配置（不提交）
│   ├── mysql-root.cnf          专用实例管理凭据（不提交）
│   └── redis.conf             专用16380实例配置（不提交）
├── scripts/                    配置、启动、停止、构建和验证脚本
├── data/                       独立 MySQL / Redis 数据及上传文件（不提交）
├── logs/                       服务日志、构建日志、进程记录（不提交）
├── .runtime/                   便携JDK、Maven、Redis、依赖缓存（不提交）
├── .gitignore
└── README.md
```

Java 后端与管理前端来自官方独立仓库，保留原有 MIT 许可证。外层目录目前没有 Git 仓库；如以后纳入统一仓库，需要自行选择保留嵌套仓库、使用 submodule，或改为普通目录。

## 日常启动 / 停止

从项目根目录运行，不需要激活 Python 虚拟环境或修改系统 JAVA_HOME：

```powershell
cd C:\path\to\sky-twin
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\start.ps1
```

脚本按 MySQL → Redis → Java → 管理前端 → 指挥大屏 的顺序启动，重复运行会复用本部署的进程。指定端口被其他进程占用时会退出，不会强行停止其他服务。只启动单个服务可传入 `-Service backend` / `frontend` / `dashboard` / `data`。

停止脚本管理的全部服务（包括通过本脚本启动的5173大屏，不停止其他进程或原8000、3306、6379）。仅停止 Java 可传入 `-Service backend`：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\stop.ps1
```

检查运行状态：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\check.ps1
```

登录及权限接口验证（仅本地；验证脚本读取本次生成的验证码，不关闭验证码功能）：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\verify-login.ps1
```

修改管理员密码后，验证脚本需传入相应账户信息，或直接通过浏览器验证登录。

## 修改代码后构建

```powershell
# Java
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\build.ps1 -Target backend

# Vue
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\build.ps1 -Target frontend
```

Java 脚本指定便携 JDK 17、Maven 3.9，缓存保存在 `.runtime/maven-repository/`。Maven 打包跳过上游测试；运行验证以本地 API 冒烟检查为准。Java 代码修改后需重新构建并停止 / 启动服务。Vue 开发服务器支持热更新。

前端重新安装依赖：

```powershell
cd .\ruoyi\frontend
npm.cmd ci --registry=https://registry.npmjs.org --cache ../.runtime/npm-cache --no-audit --no-fund
```

## 环境说明与重新配置

- Java：便携 Temurin JDK 17.0.20.1，已对官方 ZIP 校验 SHA256。
- Maven：便携 Apache Maven 3.9.16，已校验 SHA512。
- Node：本机 `C:\Nodejs-v11.9.0\node.exe`，实测版本为24.18.0；目录名不是实际版本。
- MySQL：复用已安装的8.0.43可执行文件；新建3307实例使用本目录的数据文件，不需要原3306管理员密码。
- Redis：从本机 `D:\redis` 复制8.2.1可执行文件及依赖；新16380实例使用独立配置和持久化目录。

`configure-local.ps1` 重新生成本机路径和服务配置，已有随机凭据不会重置：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\configure-local.ps1
```

重新配置前先停止本部署。如更换电脑，需准备 Node、MySQL、Redis 及 `.runtime/` 下的 JDK/Maven，然后通过该脚本的 `-MySqlBin`、`-RedisSource`、`-NodeExecutable` 参数设置路径。

首次数据库初始化由 `initialize-db.ps1` 完成；有 `.schema-ready` 标记时不重复导入，数据库存在表但缺少标记时拒绝覆盖。不要把上游 `sql/` 中的 DROP TABLE 脚本导入原项目数据库，也不要删除 `data/` 作为日常重启方式。

Windows 下较长 TEMP 路径可能导致 JDK 的 Unix-domain socket 初始化失败，启动脚本已用 `-Djdk.net.unixdomain.tmpdir` 指向较短的项目临时目录，见 [Java 官方网络属性说明](https://docs.oracle.com/en/java/javase/21/core/java-networking.html)。

## 与 SkyTwin 的业务分工

- 现有大屏：三维态势、飞行仿真、实时展示。
- RuoYi Java：用户权限与后续业务实体、订单、站点、任务的持久化管理。
- FastAPI：保留现有 Demo，后续可负责 Agent / 图像分析 / 调度算法，并通过服务接口与 Java 配合。

已实现飞行器 / 站点 CRUD、五类统一任务、轨迹、事件处置、任务摘要报告、操作记录、角色权限及鉴权 SSE。原指挥大屏5173改为读取 Java 业务数据，原 FastAPI 内存 Demo 不再参与本轮任务执行。

第一次业务表迁移：`powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\migrate-sky.ps1`（本次已执行，可重复运行）。

先登录管理端，打开「低空业务 → 统一任务管理」，创建环境监测任务，选滨江起降点与东岸物流站，填写原因，依次分配 D-01、执行；打开5173大屏查看状态。服务端完成后可查询轨迹及报告。通勤任务需两个 eVTOL 起降场、乘客数与 eVTOL 资源。

超级管理员已有全部权限；如创建新用户，可分配「低空调度员」或「低空查看者」。调度员可操作任务与告警，查看者只读，资源维护由管理员负责。权限变更后需重新登录。

仿真与后续功能边界见 [基础能力说明](../docs/FOUNDATION_IMPLEMENTATION.md)。当前没有真实飞控、Agent 自动调度、视觉识别或业务专属订单与通勤预约。

业务集成验收脚本：从项目根目录执行 `.\.venv\Scripts\python.exe -u .\ruoyi\scripts\verify-foundation.py`；会创建唯一命名的本地测试数据，验证权限、多机、任务状态机、SSE和Java重启持久化，最后清理该次测试数据。不要在正在进行自己的仿真演示时运行重启验收。

新增管理组件类型检查：在 `ruoyi/frontend/` 执行 `node ../../frontend/node_modules/vue-tsc/bin/vue-tsc.js --noEmit -p tsconfig.sky.json`，复用原大屏的 Vue TypeScript 工具。

## 官方来源与本次版本

- 后端：[RuoYi-Vue springboot3](https://github.com/yangzongzhuan/RuoYi-Vue/tree/springboot3)，RuoYi 3.9.2 / Spring Boot 3.5.16，提交 `a51a838b71b446ea27256900efe7ed2faa2a02fd`。
- 前端：[RuoYi-Vue3](https://github.com/yangzongzhuan/RuoYi-Vue3)，RuoYi 3.9.2，提交 `838965c5a18d2c61b73ec30c6e288057aaa08b63`。
- [官方文档](https://doc.ruoyi.vip/)。

### Redis 端口无法启动（Windows）

若日志出现 `bind: Permission denied`，用 `netsh interface ipv4 show excludedportrange protocol=tcp` 检查端口是否被 Windows 保留。本机原 6380 位于保留范围 6380～6479，项目现使用 16380。端口集中配置在 `config/runtime.local.json` 的 `RedisPort`；启动脚本会传给 Redis 和 Java，验收脚本也读取此配置。不要删除 Redis 持久化数据或停止其他项目的 6379 实例。
