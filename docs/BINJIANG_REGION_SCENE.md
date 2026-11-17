# 杭州滨江大范围场景

数字孪生页默认从原来的 500 米测试 GLB 切换为滨江及钱塘江两岸的离线 OSM 场景。裁剪框为 120.10～120.28°E、30.10～30.29°N，米制范围约 17.3 × 21.2 公里；它包含 OSM 标注的滨江完整行政区界，也包含周边城区，不等同于滨江行政区面积。

## 查看与操作

按原方式启动大屏，在 `/digital-twin` 查看。默认“钱塘江景”以 OSM 复兴大桥位置为视角中心；“滨江城区”看江南城区，“全域总览”框选整个裁剪框。拖动旋转、滚轮缩放；“暮色 / 日景 / 素模”切换材质。“仿真车流”可单独关闭，素模隐藏装饰和车辆。

静态资源 `frontend/public/models/hangzhou/binjiang-region.json` 含建筑足迹、道路中心线、水体/绿地多边形及滨江区界。页面加载该资源后生成合并几何，不需要 WSL，也不需要运行时请求 OSM 服务。原来的 `binjiang-test-500m.glb` 保留作为旧阶段资源，没有将同一个街区复制成大城市。

建筑外形、水体边界和道路来自 OSM；窗格、材质、树木、屋顶设备、路灯、车流是仿真外观。桥梁使用源道路的桥标记生成桥面与示意桥墩，桥面高度暂按 16 米显示。建筑有明确高度则使用高度，只有楼层数则按 3.2 米/层换算；二者均缺失时按用途推测并保留 `heightSource=inferred`。精确统计和源区界范围见 `assets-source/hangzhou/regional/region-provenance.json`。

当前仍不是照片级倾斜摄影模型。尚未接入 DEM 起伏和真实外立面；部分 OSM 建筑高度也可能存在错误。道路车流沿中心线循环运动，没有实时道路流量或信号灯数据。

## 源数据与重建

来源：[OpenStreetMap France 浙江下载目录](https://download.openstreetmap.fr/extracts/asia/china/)。本地源文件为 `assets-source/hangzhou/regional/zhejiang-20261009.osm.pbf`，约 94 MiB，下载时 HTTP Last-Modified 为 2026-10-09T00:50:43Z；这不是建筑测绘时间。保留 © OpenStreetMap contributors / ODbL-1.0 署名。

Windows PowerShell：

```powershell
# 用本机 Python 3.11；库只放在项目的 .runtime/geo-tools。
python -m pip install --target .runtime/geo-tools osmium==4.3.1 shapely==2.1.2
python scripts/build_binjiang_region.py
```

脚本使用 pyosmium 组装完整水体/行政区多边形，用 Shapely 修复、裁剪并保留内环，再投影为米。完整滨江源区界的包围盒必须位于裁剪框内，否则脚本拒绝覆盖现有输出。输出采用临时文件替换，避免运行时读到半个 JSON。

裁剪框变大时同时调整前端校验预算、默认视角和渲染成本；不要仅把一块 GLB 等比放大。后续精细模型可以按同一个地理原点替换局部建筑。

## 数据流与模块

- `CityViewport.vue` 承载画布、状态和标签；`CitySceneControls.vue` 仅接收外观/车流状态并向上发送外观、视角和开关事件。
- `useCityScene.ts` 管理加载/重试、相机、Java 业务对象和页面退出。区域解析与几何构建完成后才进入 ready；页面切换会取消 CPU 构建或释放迟到结果。
- `cityRegionData.ts` 校验原点、范围、几何、高度及完整区界覆盖；`cityRegionGeometry.ts` 保留多边形内环并生成 Y 向上的几何。
- `cityRegionScene.ts` 按 2 公里格网/材质合并几何，避免每栋楼单独提交绘制；装饰采用实例绘制并在全域采样，避免只集中在早期 OSM 对象。
- `cityTraffic.ts` 用真实道路中心线驱动最多 800 辆示意车辆，独立于 Java 的无人机和任务状态。

本版原点为 120.19°E、30.215°N，高程 0。`cityCoordinates.ts` 继续使用 MetricMapProjection：X 东、Y 上、Z 南，米制。Java 经纬度必须是 WGS84；仍未迁移原有上海演示坐标，范围外对象继续在列表中保留并提示。扩大场景不会把上海数据变成杭州数据。

## 验证记录（2026-10-11）

区域提取脚本已读取公开 PBF 并生成离线资源。前端检查覆盖范围/完整区界、建筑高度来源、非法数据拒绝、庭院孔洞与正向法线、车流沿源道路运动，以及旧坐标链路。浏览器使用隔离测试数据，不连接 Java、不写数据库，验证三种视角、外观切换、车流开关、范围过滤、下载失败重试和加载期间重新挂载；临时验证入口在结束后删除。

大场景水面曾因小街区的 0.5 米近裁剪面出现深度冲突，已改为按视距调整近面并给地面覆盖层设置 polygon offset。全域视角的雾距也随视距调整，避免总览被雾完全遮挡。检查数据与最终截图见本节后续记录。

最终记录：

- 输出 19,836 个建筑足迹对象、19,859 个道路分段、562 个水体多边形、1 个滨江区界；区域 JSON 为 9.37 MiB。15,679 个建筑对象缺失高度/楼层，使用推测高度；163 个由楼层换算，3,994 个使用源 height 属性。省级组装过程跳过 13 个无法解析的区域几何，不表示数据完整或已经实测校核。
- 源区界包围盒为 `[120.1175748,30.1387418,120.2321489,30.2390065]`，完整位于场景裁剪框。PBF SHA256：`d10c1a086ae948a2d1b380b8af3e273d857e2c0fc2ce64df20adb2603e0ee152`。
- `npm.cmd run build` 退出 0，Vue 类型检查通过；仍有已有的大包体提示。`node --test tests/cityRegion.test.mjs tests/cityAppearance.test.mjs tests/cityCoordinates.test.mjs`：10 项通过。
- 1440 × 900、DPR 1 的隔离浏览器：江景累计 475 次绘制、1,476,920 个三角形、462 个已上传几何、15 个纹理；全域 1,235 次绘制、1,907,331 个三角形、1,222 个已上传几何、15 个纹理。计数含后处理；全域首次显示会上传此前被视锥裁掉的几何，这是缓存增长。
- 最近 180 帧 RAF 间隔：江景 P50/P95 约 6.3/6.3 ms，全域约 6.3/6.7 ms。记录来自隔离 IAB 浏览器，不是 GPU 时间或用户设备帧率保证。树木/设备/路灯/车辆上限为 8,000 / 1,500 / 2,400 / 800，按 2 公里/材质合并为 1,203 个几何批次。
- 重复进入相同江景恢复为 462 个已上传几何、15 个纹理，只有一个 canvas。最终 HTTP 503 测试重试成功，加载中重新挂载后正常恢复；正式组件渲染无新增控制台 error。最早的隔离测试曾缺失任务 progress 字段，修正测试数据后消失；没有为此修改业务组件。
- 截图为 `docs/verification/binjiang-region-river.png` 与 `binjiang-region-overview.png`，明确标注隔离数据/未连接 Java。临时测试入口已删除。
