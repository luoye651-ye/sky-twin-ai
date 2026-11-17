# 独立面试演示与质量门禁

需要国内网络直接访问的参赛入口，先看 [国内公网演示指南](DOMESTIC_DEMO_GUIDE.md)。下面的独立样例仍是本机隔离环境，不能替代真实业务入口。

独立样例入口不是生产环境，也不是主系统登录的替代方式。它是单独的Python进程和生产构建的Vue页面，默认仅监听本机 `5180/8003`，不需要Java/MySQL/Redis，不连接现有业务，不允许外部模型调用。

## 准备与启动

前提：Windows、本项目 `ruoyi/config/runtime.local.json` 已按原安装说明配置Node路径，Python 3.13和Node 22可用。

```powershell
cd frontend
npm ci
cd ../agent
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
cd ..
powershell.exe -NoProfile -ExecutionPolicy Bypass -File deploy/start-demo.ps1
```

已存在 `.venv` 时不要重新创建。首次缺少本地Embedding时，脚本只下载固定公开Embedding模型并核对哈希；不会下载训练集或调用付费LLM。之后离线可运行合成流程、知识导入和本地检索对照。模型下载、依赖安装需要正常网络。

打开 http://127.0.0.1:5180/ai-workbench 。脚本首次生成 `agent/.runtime/demo/credentials.json`，账号为demo，密码为随机值，在自己电脑打开该文件查看；不把文件上传、截图或提交仓库。此环境不使用主系统验证码、账号或令牌，不改变主系统认证配置。独立Cookie名为SkyTwin-Demo-Token，避免同一localhost的不同端口覆盖原Admin-Token。

首次启动会构建前端和本地知识索引；代码及文档未变化时可加 `-SkipBuild` 只跳过前端构建。演示顺序：登录→运行合成样例→查看检查点及轨迹→上传一份可公开的规程→试验本地检索→运行语义/混合检索对照→导出JSON。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File deploy/stop-demo.ps1
```

只停止经路径/PID/启动时间核对的demo-web和demo-agent进程；保留演示数据。工作台的“重置我的演示记录”只删除独立数据库中当前演示账号的AI运行、轨迹和文档，不删除文件、其他账号或任何Java记录。

## 真实业务模式

原平台仍为 http://127.0.0.1:5173/ai-workbench ，使用原若依身份。Java保持唯一任务/订单/事件状态源；Python SQLite仅保存AI执行、检索资料和评测产物。业务写操作仍由Java按sky:operate/sky:manage验收。

模型调用仅在用户明确选择真实分析或真实评测并勾选证据外发授权后发生。报告与原聊天沿用既有触发方式；不会因为启动或查看页面自动调用模型。模型配置沿用 `agent/.env`。可选环境变量：

```dotenv
# 人工填写选用模型的每百万Token单价；币种由运营者明确，本项目不内置实时价格。
SKYTWIN_PRICE_INPUT_PER_MILLION=
SKYTWIN_PRICE_OUTPUT_PER_MILLION=
# 同一已配置提供方可用的另一个模型名，不接受客户端传入任意服务URL。
SKYTWIN_EVAL_MODEL_SECONDARY=
# 可选技术产物库路径；不可指向别的实例正在使用的文件。
SKYTWIN_ARTIFACT_DB=
```

默认真实技术记录在 `agent/.runtime/workbench.sqlite`，独立样例在 `agent/.runtime/demo/artifacts.sqlite`。单实例、单worker设计，不支持多个Agent进程共享同一SQLite文件恢复任务；横向扩展需改为服务端作业队列/租约。

## 持续集成与交付边界

`.github/workflows/quality.yml` 配置了前端检查/构建、Python无外部模型隔离测试及Java打包。`requirements.lock.txt` 固定本机验证环境中的版本，Windows专用依赖带平台条件。工作流须进入真实仓库后才会由GitHub触发，本轮本地验证不能冒充远端CI运行结果。

上述独立样例仍仅供本机使用，不把关闭验证码的独立本机样例直接暴露到公网。主系统新增的 Sites + 受保护本机隧道部署见 [公网演示指南](PUBLIC_DEMO_GUIDE.md)，它保留 Java 登录与验证码，使用专用业务演示账号，连接现有业务环境。代码仓库应保留既有真实开发历史，不倒填提交、不自动公开本地秘密或比赛资料。
