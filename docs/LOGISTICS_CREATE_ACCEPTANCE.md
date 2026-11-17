# 创建配送订单：编译和接口验收

验收日期：2026-10-15（Asia/Shanghai）。本阶段仅覆盖订单创建，不包含查询页面、派机或送达。

## 本次实际修复

用户已亲手创建输入、服务和控制器三个业务类。第一次编译发现服务类两处根因：

```java
// 错误：方法返回值与 equals 调用之间少了点号。
x.startStationId()equals(x.endStationId())

// 修正：读取起点编号，然后调用字符串的 equals 方法。
x.startStationId().equals(x.endStationId())
```

另一个 `}` 在生成订单编号之后提前关闭了 `create`，导致后续 `db.update` 和 `return` 落在方法外。已将方法结束位置移至 `return orderId;` 之后，并保留外层类的结束括号；未改变用户的业务流程。编译报出8处错误，但并不等于有8个独立问题，括号错误会造成后续连锁诊断。

修复后独立Java17编译通过，随后完整Maven打包出现 `BUILD SUCCESS`。打包脚本使用 `-DskipTests`，不把该构建当作接口测试；下面另行运行了真实HTTP和数据库验收。

## 第一步：从项目根目录编译、启动

终端当前目录应为 `C:\path\to\sky-twin`。以下命令逐条执行，上一条失败就先看错误，不继续往下：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\stop.ps1 -Service backend
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\build.ps1 -Target backend
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\start.ps1 -Service data
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ruoyi\scripts\start.ps1 -Service backend
```

- 停止Java再打包，是为了避免Windows锁定正在运行的jar。
- `BUILD SUCCESS` 表示项目打包通过，不代表接口一定正确。
- 已运行的专用MySQL/Redis会被复用；不操作原3306/6379服务。
- 修改Java源码后，需要重新打包和重启Java；不是只刷新网页。

本次已经完成以上操作，若只复跑接口测试，不需要重新构建。

## 第二步：亲手运行本地验收脚本

在项目根目录执行：

```powershell
python .\ruoyi\scripts\verify-logistics-create.py
```

默认经管理端代理 `http://127.0.0.1:5174/dev-api` 请求真实Java服务。如只启动Java，管理端5174未启动，可使用：

```powershell
python .\ruoyi\scripts\verify-logistics-create.py --base-url http://127.0.0.1:8081
```

脚本仅支持本机专用环境，自动处理本地测试账号登录和验证码，不打印令牌或密码。默认账号为当前开发环境的admin；如果已修改密码，可通过进程环境变量 `SKYTWIN_TEST_PASSWORD` 提供，勿把密码提交到代码中。

每次使用不同测试标记，创建两处杭州测试站点及一个订单，不派机、不启动飞行。在 `finally` 中按本次唯一标记清理测试订单、任务、站点和业务审计，退出本次测试登录。若依自己的系统操作/登录日志会保留真实测试记录。

## 第三步：对照返回和数据库变化

Java接口：`POST /sky/logistics/orders`。示意请求（测试脚本会用其本次创建的站点编号替换起终点）：

```json
{
  "cargoName": "验收药品",
  "weight": 2.5,
  "startStationId": "本次测试起点ID",
  "endStationId": "本次测试终点ID",
  "deadlineMinutes": 10,
  "reason": "本次测试唯一标记"
}
```

本次实际结果：

| 场景 | JSON code | 结果 | 本场景新增订单/任务/业务审计 |
|---|---:|---|---|
| 正常创建 | 200 | 返回订单ID；关联物流任务处于created；期限约10分钟；创建人为admin；订单重量=任务载荷=2.5 | 1 / 1 / 2 |
| 名称为空字符串 | 500 | 货物名称不能为空 | 0 / 0 / 0 |
| 名称只有空格 | 500 | 货物名称不能为空 | 0 / 0 / 0 |
| 起点等于终点 | 409 | 起点与终点不能相同 | 0 / 0 / 0 |
| 终点站不存在 | 404 | 记录不存在或已移除 | 0 / 0 / 0 |
| 重量2.555 | 500 | 重量最多保留两位小数 | 0 / 0 / 0 |
| 任务写入后，订单写入被模拟故障拒绝 | 500 | 返回本次模拟故障标记 | 0 / 0 / 0 |

上述HTTP状态实际均为200。若依的全局异常处理将业务/校验结果放在JSON `code` 中：HTTP请求成功传输不等于业务成功。输入校验失败的code=500是项目当前约定，不是本次测试误判；本阶段未修改若依公共异常处理规则。

正常请求产生两条 `st_audit`：一条 `task.create`、一条 `order.create`。系统操作日志在 `sys_oper_log`，不能与业务审计混为一谈。

## 为什么还要故意制造一次数据库写入失败？

空名称在 `@Valid` 阶段就被拒绝，没有执行创建任务，无法单独证明事务回滚。

额外测试在专用数据库中创建了一个临时 `BEFORE INSERT` 触发器：仅当货物名称严格等于本次随机测试标记时拒绝订单写入，其他订单不受此条件影响。这是集成测试的故障注入，不进入Java业务代码。

执行到订单写入时，前面的 `sky.createTask` 已经执行了任务和任务审计INSERT。随后订单INSERT报错，异常向外抛出；`LogisticsService.create` 的事务将前面的写入回滚，因此查不到任务和业务审计残留。临时触发器在该用例结束后立即删除，异常路径也有finally清理。本次已确认触发器剩余数为0。

测试数据清理与事务回滚是两件事：每个失败用例都先查询并断言其订单/任务/审计为0，之后才执行最终清理，不能用“测试最后删除了数据”冒充“事务自动回滚”。

## 第四步：阅读报告，完成一次自己的复核

文件位置：

```text
.\ruoyi\logs\logistics-backend-build.log
.\ruoyi\logs\logistics-create-verification.log
.\ruoyi\logs\logistics-create-verification.json
```

JSON报告中查看：

1. `passed` 为true。
2. `cases` 中正常用例 `after` 是订单1、任务1、业务审计2。
3. 失败用例 `before` 与 `after` 都是0。
4. `late_order_write_failure` 确实收到故障标记，且 `after` 全部为0。
5. `cleanup` 的订单、任务、业务审计、站点和临时触发器全部为0。

因为测试数据已清理，验收结束后Navicat看不到测试订单是预期行为，不是创建失败。报告保存了正常订单与任务的关联快照。

学习检查：用自己的话解释“编译通过”“接口code=200”“事务回滚”“最终清理”的区别。这不是继续开发的答题门槛；有不理解的部分直接指出即可。

当前未覆盖订单查询页面、调度、电量/载重派机、飞行跟踪、送达确认或重启恢复，这些属于后续小功能。
