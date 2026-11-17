# 确认送达接口验收

日期：2026-10-18。用户已亲手保存 `LogisticsInputs.Deliver`、服务 `deliver` 方法和控制器入口；本轮未修改这三个业务文件。

## 已执行

完整 Maven 打包 `BUILD SUCCESS`，重启本项目 8081 Java 后，经大屏 `5173/java-api` 对实际接口进行验收。首次构建时，停止后端后又有 Java 进程启动，打包阶段无法重命名被占用的 JAR；重新依次停止、打包、启动后成功。该次失败不是 Java 源码语法错误。

接口：`POST /sky/logistics/orders/{订单id}/deliver`，请求体 `{"reason":"确认原因"}`，要求 `sky:operate`。

脚本：`ruoyi/scripts/verify-logistics-deliver.py`。报告：`ruoyi/logs/logistics-deliver-verification.json`。

本次结果：`passed=true`，22 项检查通过。

| 检查 | 实际结果 |
|---|---|
| 待分配、已分配、执行中 | 拒绝确认，订单及送达审计不变 |
| 已取消、失败任务 | 拒绝确认，订单及送达审计不变 |
| 正常仿真 | 自建临时货运无人机、站点和订单，由 Java 仿真完成，保存 21 个轨迹点 |
| 空原因、纯空格、超过500字符 | 输入校验拒绝，订单不变 |
| 不存在订单、误传任务编号 | 返回业务码404 |
| 匿名、仅查看者 | 分别被401/403拒绝；查看者仍可GET查询 |
| 两次并发确认 | 一次200、一次409；状态delivered，确认人admin、服务端时间存在，送达审计仅1条 |
| 请求中伪造actor | 未采用；确认人仍为登录身份admin |
| 再次确认 | 409，确认时间和审计数量保持不变 |
| 更新后审计写入故障 | 仅对该次测试订单/原因触发临时数据库故障；订单状态、确认人和时间全部回滚 |
| 列表查询 | 同时返回订单delivered和关联任务completed |
| 清理 | 本次订单、任务、轨迹、报告、事件、资源、业务审计和临时触发器均为0；临时查看者账号访问已移除 |
| 用户原订单 | 确认状态、确认人、确认时间与测试前一致，未替用户确认送达 |

临时账号通过若依软删除，系统登录/操作日志保留；不声称数据库中连系统审计记录也被删除。测试不使用已有飞行器，不修改原有3306 MySQL或6379 Redis，不执行实机飞行。

若依有些失败响应的 HTTP 状态仍为200，应同时读取 JSON 内 `code`，不能只凭 HTTP 200 判断业务成功。

## 用户复跑

在项目根目录执行，复用已启动的服务：

```powershell
cd C:\path\to\sky-twin
D:\miniconda\python.exe .\ruoyi\scripts\verify-logistics-deliver.py
```

看到最后 `PASS: logistics delivery acceptance completed`，再打开 JSON，检查 `passed`、`cases` 中失败请求的 `before/after`、`concurrentBusinessCodes` 和 `cleanup`。脚本默认只连接本地专用部署，使用独立随机名称并在最后清理，不输出或保存登录密码及令牌。

如果修改了 Java 源码，需要先依次执行下列命令，各步成功后再执行下一步：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\stop.ps1 -Service backend
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\build.ps1 -Target backend
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\start.ps1 -Service backend
```

学习点：编译检查源码；重启加载新代码；HTTP和数据库验收检查业务规则。它们不是同一件事。`@Transactional` 的证据是审计写入失败后订单更新也撤销；`FOR UPDATE` 的证据是并发请求只产生一次有效确认。

## 下一小步

用户复跑并对照报告后，在物流订单表格添加“确认送达”按钮，调用本轮已验收接口。仅有操作权限、订单created且任务completed时提供入口；处理提交中、原因输入、失败保留及成功刷新。页面按钮尚未实现，不能将物流完整交互标记为完成。重启后的订单查询恢复未在本轮单独验证。
