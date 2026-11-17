# SkyTwin环境发现与应急处置流程

## 提交发现证据

人工证据闭环要求上传图片、位置、采集时间及人工标注，并关联执行中或已完成的environment环境巡检任务。位置必须是有效WGS84经纬度，采集时间应在过去365天至未来5分钟内；标注框用0～1比例且须完整位于图片内。这条人工标注流程不是AI模型置信度结果；当前AI巡逻列表另有独立的离线识别记录，不自动转入本流程。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/EnvironmentService.java：create；EnvironmentRules.java：coordinate、observed、box。

## 人工复核与事件生成

发现初始为pending_review待复核。只有待复核发现才能复核，不能重复生成事件。人工confirm确认时创建河道漂浮物事件，发现转为confirmed；未确认的发现转为rejected。复核记录严重等级、原因、操作者和时间。仅检测到漂浮物并不意味着已经人工确认，更不代表已执行真实清理。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/EnvironmentService.java：review；ruoyi/backend/sql/sky_twin_v8_environment.sql。

## 安排应急侦察与重试

只有confirmed或in_response且未结案的发现可安排应急侦察。此前每次处置任务都必须已completed、cancelled或failed，存在未结束任务时拒绝再次安排，防止重复占用资源。服务端创建rescue类型的侦察仿真任务，并让航线经过事件位置；发现进入in_response。high、medium、low严重等级分别映射优先级3、2、1。创建侦察任务不等于已经分配或起飞，之后仍走现有任务引擎及空域/多机安全校验。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/EnvironmentService.java：respond；EnvironmentRules.java：priority。

## 结案条件与处置后证据

只有in_response发现可以结案。所有处置任务不能仍为created、assigned或executing，且最新一次应急侦察必须completed；取消或失败不能算处置成功。还需最新任务有事件点10米内、飞行高度大于0的服务端轨迹；处置后图片SHA-256必须不同于发现图，并提交人工处置说明。通过后发现为closed、事件为resolved，生成含证据、轨迹及审计关联的归档报告。这只证明软件流程关联，不证明真实清理效果或实机救援。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/EnvironmentService.java：close。

## 为什么不能直接从通用事件接口结案

如果事件关联环境发现记录，SkyService.resolveEvent会拒绝通用结案，要求通过环境证据闭环完成侦察和处置后证据。不能跳过人工复核、最新侦察完成、轨迹检查和处置后图片。Agent当前只有只读工具，可以解释条件，不能代替人工确认或调用结案写接口。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/SkyService.java：resolveEvent；EnvironmentService.java：close。
