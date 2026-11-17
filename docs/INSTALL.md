# 安装运行指南

## 环境与依赖

当前完整主系统以 Windows PowerShell 为主。Node.js 22 或兼容已验证版本、JDK 17、Maven 3.9、MySQL 8、Redis，以及 Python 3.13。视觉环境另按 `ai/env-spec.json` 和 `ai/requirements-lock.txt` 准备；不要合并 Agent 与 YOLO 的虚拟环境。

| 模块 | 依赖入口 |
|---|---|
| 指挥前端 | `frontend/package.json`、`package-lock.json` |
| 管理前端 | `ruoyi/frontend/package.json`、`package-lock.json` |
| Java | `ruoyi/backend/pom.xml` 与子模块 POM |
| Agent | `agent/requirements.txt`、`requirements.lock.txt` |
| YOLO | `ai/env-spec.json`、`requirements-lock.txt` |

## 首次配置

1. 克隆仓库到独立目录。数据服务使用专用 3307 / 16380，不改动原有 3306 / 6379。配置、初始化和主系统启动前阅读 `ruoyi/README.md` 与脚本参数。
2. 将 JDK 17、Maven 3.9 解压到 `ruoyi/.runtime/`，目录名称分别匹配 `jdk-17*`、`apache-maven-3.9*`。安装可用的 MySQL 二进制和兼容 Windows Redis 的程序及依赖。
3. 在根目录执行以下命令，按自己机器路径替换参数：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\configure-local.ps1 -MySqlBin 'C:\Program Files\MySQL\MySQL Server 8.0\bin' -RedisSource 'D:\redis' -NodeExecutable 'C:\Program Files\nodejs\node.exe'
npm.cmd ci --prefix frontend
npm.cmd ci --prefix ruoyi/frontend
py -3.13 -m venv agent/.venv
.\agent\.venv\Scripts\python.exe -m pip install -r agent/requirements.lock.txt
Copy-Item agent/.env.example agent/.env
```

已有 `.env` 不重复复制覆盖。在本机填写 DeepSeek API Key；网页使用自己的 Java 登录身份，`SKYTWIN_TOKEN` 仅为命令行工具可选身份。首次 Embedding 需要下载公开模型并联网校验，后续可使用本地缓存。模型支持图片输入的能力以实际接口验证为准。

`configure-local.ps1` 自动生成本机工具路径及随机数据库、Redis、JWT 凭据；它们不随仓库分发。根 `.env.example` 是字段说明，并非启动脚本自动加载的统一文件。配置含义见该模板，Agent 实际读取 `agent/.env`。

4. 仅在全新、空的专用数据目录初始化 MySQL。请在另一台电脑或停止原部署后操作，不能与原项目同时占用 3307 / 16380。已有实例不重复执行初始化；如果存在数据而无法识别，先排查，不删除：

```powershell
# 使用自己安装的 mysqld.exe；配置必须指向本仓库新生成的 mysql.ini
& 'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe' "--defaults-file=$((Resolve-Path .\ruoyi\config\mysql.ini).Path)" --initialize-insecure
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\start.ps1 -Service data
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\initialize-db.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\migrate-sky.ps1
```

`--initialize-insecure` 仅用于新建的回环监听实例引导；随后 `initialize-db.ps1` 设置本机随机 root 密码和业务用户，不以无密码实例提供演示服务。

5. 构建 Java 并启动：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\build.ps1 -Target backend
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\start.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\check.ps1
```

业务表按 `ruoyi/backend/sql/` 的迁移增量处理。已有数据时保留原目录和初始化标记，不用删除数据或向个人数据库导入上游重建脚本。初次独立数据库的默认若依账号见 `ruoyi/README.md`，修改密码后再做公网演示。

## 正常使用与停止

主前端 5173、管理前端 5174、Java 8081、Agent 8002。登录后从 Agent 指挥、环境发现、任务管理及 AI 工作台体验同一业务链。真正调用外部模型会按本机配置产生费用；观察记录和仿真结果分别标识。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\stop.ps1
```

只停止脚本管理且路径、PID、启动时间匹配的进程。国内演示另用 `deploy/start-domestic-demo.ps1` 与 `stop-domestic-demo.ps1`，见同目录指南。cpolar 客户端及认证在本机配置，Token 不提交。

## 模型与数据

仓库不含训练集、检查点、Python 环境、本地数据库或历史业务图片。YOLO 上传检测也需要发布模型与元数据，离线巡逻还有数据完整性要求；详见 [MODEL_DATA.md](MODEL_DATA.md)。缺少资源时不能把旧检测图片当成新推理成功。

## 开发检查

```powershell
cd frontend
node --test tests/*.test.mjs
npm.cmd run build
cd ../agent
.\.venv\Scripts\python.exe -m unittest test_vision_chat test_workbench test_demo_service test_business_tools test_dispatch_tools test_conversation test_chat_service test_rag_agent test_aircraft_agent test_rag -q
```

以上为协议和隔离验证，不调用付费模型。Java 规则检查见 `ruoyi/scripts/verify-*-algorithm.ps1`；真实业务验收可能写测试记录或重启服务，先在独立环境按各脚本说明执行。新电脑完整安装尚未在本轮重新验证。
