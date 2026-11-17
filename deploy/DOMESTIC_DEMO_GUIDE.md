# 国内网络演示入口

当前入口以本机 `.runtime/domestic-demo.json` 的 `publicOrigin` 为准，本次已分配 `https://968b1d0.r9.cpolar.cn`。这是 cpolar 中国区的随机 HTTPS 地址；地址可能变化，提交前请确认，不要继续使用旧 chatgpt.site 作为国内评审入口。

2026-11-16 新鲜验收：5 项本机隔离检查通过；明确使用 `ProxyHandler({})` 禁用 HTTP 代理后，公开首页、SPA 深链接、同源 API 配置、主脚本下载/gzip、验证码、Agent 健康、未登录业务拒绝和系统管理接口阻断共 8 项通过。未执行本次国内入口的真实账号登录/业务写操作或付费模型调用。

浏览器 → cpolar 中国区 HTTPS 隧道 → 本机 5182 → 同一套 Java / Agent。网页、三维资源、登录和 API 全部通过这个入口，不需要访问 Sites，也不需要访客配置代理。连接器的子进程显式清除代理环境变量。Java 仍拥有全部业务状态，没有复制任务数据库。

## 下次开机

保持电脑联网并暂停睡眠，在 PowerShell 执行：

```powershell
cd D:\cursor\project\sky-twin
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\deploy\start-domestic-demo.ps1
Get-Content .\.runtime\domestic-demo.stdout.log -Tail 5
```

看到 `Domestic demo ready: https://...` 后使用该地址。脚本检查本机数据服务、Java、Agent，再启动项目专用 cpolar 连接器与网站；后台运行，不需要打开 Codex 或继续使用之前的 Sites 启动命令。

仍使用 `sky_demo` 登录，密码自行在本机 `.runtime/public-demo-credentials.json` 查看，验证码照常填写；不要录下密码、Token 或本机秘密配置文件。业务操作作用于现有本机数据，演示时使用新的测试记录。

## 演示结束

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\deploy\stop-domestic-demo.ps1
```

只按 PID、程序路径和启动时间核验并停止本轮国内入口及 cpolar 子进程，不停止原 Java、Agent、MySQL、Redis。关机或停止后，国内页面也会停止提供服务，因为网页文件现由本机提供。

## 认证与费用

本项目使用官网签名验证通过的 cpolar 3.3.12 客户端，解包在 `.runtime/cpolar-portable`，没有注册 Windows 服务，也没有启动默认 SSH/远程桌面隧道。Token 由用户通过 `configure-domestic-demo.ps1` 的隐藏输入配置，仅存项目忽略目录 `.runtime/cpolar-skytwin.yml`；后续启动直接复用，不要再次发送 Token。

客户端只建立本项目 HTTP/HTTPS 通道，显式关闭调试抓包，只从隧道建立日志提取 HTTPS 地址，不输出认证日志。域名变化时本机网站会跟随更新，浏览器需要改用新地址并重新登录；随机地址不等于永久固定网址。

官方免费档标注 1Mbps 和随机二级域名；低带宽下三维场景首次加载可能较慢，本机入口已支持文本/JSON/脚本等 gzip 与静态资源缓存。是否需要固定域名或更高带宽，先根据账号现有权益决定，不自动购买。查看页面及健康检查不调用模型；主动使用真实 DeepSeek 功能仍会按原配置计费。

来源：[cpolar 官方套餐](https://www.cpolar.com/pricing)、[官方文档](https://www.cpolar.com/docs)。

## 验收范围与排查

- `.runtime/domestic-verification.json`：本次禁用 HTTP 代理后的公开页面、资源配置、健康及访问控制记录。
- `.runtime/domestic-demo.stdout.log`：当前分配地址和自动重连状态。
- `.runtime/domestic-demo.stderr.log`：网站/连接器错误；不要把包含秘密的配置文件作为日志上传。
- 必须再用手机流量或另一条国内网络在关闭代理时打开地址，确认评审网络体验；不声称所有运营商、地区或校园网都已通过。
- 本次未自动经 cpolar 传输真实业务快照或付费模型图片；既有 Java/Agent 登录权限保持，未改用户密码。进一步自动验证真实登录/业务内容需对该国内服务链路取得相应授权。

旧 Sites 页面仍是历史部署，相关启动脚本保留，避免破坏旧源码。它不参与此入口的运行；之后使用本指南中的 domestic 命令。
