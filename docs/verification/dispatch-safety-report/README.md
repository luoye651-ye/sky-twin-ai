# SkyTwin AI 调度与安全测试佐证

本目录支撑项目简表中的三项内部自测指标：可分配任务累计数506对487、与穷举最优目标值一致的用例占比100%对57.5%、8个违规候选的误接纳数8对0。它不是第三方检测报告、商用竞品测评或实机安全证明。

## 内容

- `SummaryBenchmark.java`：沿用原`summary-offline-v1`协议，固定随机种子521、200组、每组4任务4飞行器；另有8个违规候选和4个合法候选。新增逐例CSV，不改变原随机生成顺序、基线或目标函数。
- `verify-report.ps1`：编译现有业务优化器、已有409项检查和本目录基准；不启动服务，不读取秘密配置，不连接数据库或付费模型。
- `evidence/benchmark.json`：本次实测汇总。
- `evidence/random-cases.csv`：200组逐例结果，包括双方分配数量、优先级、成本及穷举目标值。
- `evidence/candidate-cases.csv`：12个候选的输入、两种接纳结果及完整约束拒绝原因。
- `evidence/run-manifest.json`：运行时间、JDK版本及输入源文件SHA-256。
- `evidence/algorithm-checks.log`：现有409项检查的实际输出。

PDF《SkyTwin AI 调度与安全测试说明》位于项目提交材料的正式补充材料目录。建议将PDF与本目录一起放进源码ZIP，保持本目录的项目相对位置；业务优化器和原有检查代码位于`ruoyi/backend/ruoyi-admin/src/`，无需复制第二套实现。

## 复现

从项目根目录运行，要求JDK 17或更新版本（本次实测使用JDK 17）：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\docs\verification\dispatch-safety-report\verify-report.ps1
```

若未配置项目本地运行时，请先让`java`与`javac`指向同一个JDK，或显式指定JDK目录：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\docs\verification\dispatch-safety-report\verify-report.ps1 -JdkHome 'C:\实际的JDK目录'
```

默认新结果输出到`tmp/dispatch-safety-report-replay/`，不会覆盖本次封存证据；编译产物输出到`tmp/dispatch-safety-report-classes/`。脚本若找到`ruoyi/config/runtime.local.json`，仅读取其中的JDK位置，不读取`local-secrets.json`。移交源码时不需要附带本地配置。

## 口径

1. 506与487是200组的累计分配数量，不是单次派出506架飞机，也不是实际完成订单数。
2. 一致率比较的是“数量最大、优先级和最大、成本最小”的目标值，不要求唯一派机组合相同；不代表所有业务场景均最优。穷举复用了相同候选可行性与成本，因此它验证组合优化一致性，不独立证明约束定义完备。
3. `(506-487)/487×100%=3.9014%`；`200/200=100%`、`115/200=57.5%`，相差42.5个百分点（42.5 pp）；`(8-0)/8×100%=100%`。
4. “仅空闲状态校验”是人为移除业务约束的消融基线，不是历史系统或国内竞品。8个违规候选全部被拦截，只说明本组规则样例通过，不等于禁飞区、多机冲突或实机安全达到100%。
5. 不测试数据库事务、HTTP权限、真实起飞、北斗实信号、视觉识别精度或LLM能力；这些模块不能借用本报告的通过率。
