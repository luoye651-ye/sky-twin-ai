# SkyTwin 公网演示

**国内网络演示请优先使用 [国内入口指南](DOMESTIC_DEMO_GUIDE.md)。以下保留的是旧 Sites 方案；它不能作为已通过国内无代理验收的入口。**

演示入口：https://skytwin-ai-demo.spicyangel15.chatgpt.site

专用账号：`sky_demo`。密码在本机 `.runtime/public-demo-credentials.json`，自行打开查看；不要把该文件上传、录屏或提交。验证码照常填写。此账号有低空调度员业务权限，没有系统管理员权限；资源配置等功能仍按各自业务权限检查。

2026-11-16 部署验收：公开首页、`/general`、`/ai-workbench` 和运行配置均返回 200；真实公网链路通过专用账号登录、一次业务快照、首个 SSE 实时帧、Agent/看图配置健康及退出令牌失效检查。14 项隔离测试和前端生产构建通过。此次未调用付费模型，也未执行任务写入；不代表全部交互、业务写操作或不同地区网络均已验收。内置浏览器已打开页面，但自动化状态读取超时，未完成逐页视觉验收。

## 平时怎么用

在项目根目录运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File deploy/start-public-demo.ps1
```

保留电脑开机、网络连通，暂停睡眠。后台会启动本轮网关与 SSH 隧道，并检查业务依赖；无需保留可见终端窗口。首次部署需要的 Sites 站点和秘密配置已经登记，不要重复创建站点。

入口页面和接口入口都是固定地址。免费 localhost.run 隧道内部地址会变化，连接器自动更新云端路由，不需要改前端网址。更新期间的短暂断连、免费服务的速率/流量限制、网络或电脑休眠仍可能使业务暂不可用；不承诺全天在线。

## 演示完怎么关

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File deploy/stop-public-demo.ps1
```

只停止本轮拥有并校验过的网关和隧道进程，保留原 Java、Agent、MySQL、Redis 和全部数据。网站静态页面仍可打开，业务接口将提示本机隧道不可用。

## 路径与保护

浏览器 → Sites 静态前端 → Sites API 网关 → localhost.run HTTPS/SSH 隧道 → 本机 5181 网关 → Java 8081 / Agent 8002。

- Java 仍是任务、订单、事件的唯一状态源；未迁移数据库，未建立第二套任务状态。
- 云端 R2 仅存当前隧道地址与更新时间，不存业务记录。
- 接口网关先检查隧道的随机挑战签名，再转发凭据；原始隧道还要求服务端密钥，密钥不出现在浏览器代码中。
- 本机网关只开放平台登录和低空/Agent 业务接口，阻断系统管理、文件目录、任意上游和路径穿越。公网只允许专用演示账号登录。
- 此入口连接现有业务环境，已授权用户的业务操作会改变真实本机记录。使用新建测试记录演示，不随意处置原有任务。
- 查看页面和健康检查不调用模型。主动发送自然语言或看图问题等真实模型功能仍按现有 DeepSeek 计费；不要公开分享演示密码。

## 出问题先看哪里

- `.runtime/public-tunnel.stdout.log`：应出现 `Registered active tunnel with fixed API bridge`。
- `.runtime/public-tunnel-state.json`：当前内部隧道及最后更新时间。
- `.runtime/public-gateway.stderr.log`：本机网关错误。
- `.runtime/public-verification.json`：最后一次完整只读链路验收结果；文件未生成时不能视为完整验收通过。
- `deploy/verify-public.py`：登录、快照、首个实时帧、配置健康及退出检查。经公网运行会传输登录凭据和业务快照，只有获得相应完整链路授权时才运行；不调用模型或修改任务。

前端托管项目为 `deploy/sites-skytwin`，接口托管项目为 `deploy/sites-api-bridge`。两处 `.openai/hosting.json` 是已有站点身份，后续更新必须复用。网站发布仍使用 Sites 官方源同步、保存版本与部署工具，不把本地秘密文件加入托管源码。
