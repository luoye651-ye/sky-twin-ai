# 滨江 GLB 场景接入

此文保留 500 米测试 GLB 阶段的实现记录。当前数字孪生页默认已切换为大范围滨江及钱塘江两岸场景，现行资源、操作及范围见 [BINJIANG_REGION_SCENE.md](BINJIANG_REGION_SCENE.md)。

数字孪生页使用 OSM2World 导出的滨江 GLB 作为地理底座，保留建筑几何、地理位置和米制尺寸。默认展示暮色仿真外观；可切换日景或原始 GLB 材质。业务数据仍由 Java 提供。

## 查看模型

1. 按项目原有方式启动 Java 和大屏，在 `http://127.0.0.1:5173/digital-twin` 登录。
2. 页面自动加载模型。拖动旋转、滚轮缩放；“复位视角”重新框选整个模型。
3. 下载或解析失败时显示错误和“重新加载”，不会退回旧的虚构建筑。
4. “暮色”显示蓝灰外立面、窗光和路灯；“日景”关闭窗光，使用明亮照明；“原始”恢复 GLB 材质并隐藏新增装饰。“街区近景”放大，“复位视角”框选整个街区。

运行资源放在：

```text
frontend/public/models/hangzhou/binjiang-test-500m.glb
frontend/public/models/hangzhou/binjiang-test-500m.manifest.json
```

源 OSM、导出配置和原始 GLB 保留在 `assets-source/hangzhou/`。`public` 中的文件在开发和构建后均可通过 `/models/hangzhou/` 访问；代码用 Vite 的 `BASE_URL` 拼接路径，以支持有路径前缀的静态资源部署。

## 飞行器与建筑如何对齐

加载链路：

```text
CityViewport.vue → createCityScene → 读取 manifest → GLTFLoader 加载 GLB
Java snapshot → aircraft / stations / tasks → sync → WGS84 转米制坐标 → 同一 Three.js scene
```

- `frontend/src/components/business/CityViewport.vue`：承载画布、加载提示、范围外提示、重试和相机复位按钮。
- `frontend/src/views/DigitalTwin/useCityScene.ts`：加载模型、设置灯光和相机、绘制业务对象、退出时释放资源。
- `frontend/src/views/DigitalTwin/cityCoordinates.ts`：与 OSM2World 一致的 MetricMapProjection；X 向东、Y 向上、Z 向南。正北会得到负 Z。

模型原点为 **120.210000°E，30.204000°N**。该位置映射到 X=0、Z=0；120 米高度映射到 Y=120。模型和业务对象均使用米，不再沿用之前的横向 `0.06`、高度 `0.15` 缩放。贴地飞行器仅有最小 4 米的图标显示高度，方便观察。无人机符号也放大至约 12 米宽用于辨认，不代表实机外形尺寸；标签显示 Java 原始高度。

请勿单独调用 `model.scale.setScalar(...)` 或 `model.position.sub(center)`：那会让建筑离开其地理位置，业务航线却仍在原位置。相机根据包围盒调整视角，模型本身保持原始变换。

## 配置滨江业务坐标

现有种子数据在 **121.47°E、31.23°N（上海）**，与滨江模型不在一个地方。页面保留这些数据在左侧列表，但不会把它们画进滨江地图；范围外数量会显示在场景提示中。

在若依“业务管理”中，将需要演示的站点、飞行器配置为这个模型覆盖范围内的 **WGS84** 坐标：

| 项目 | 范围 |
| --- | --- |
| 经度 | 120.2075 ～ 120.2125 |
| 纬度 | 30.2015 ～ 30.2065 |

以下仅为显示对齐用的测试点，不代表实地起降许可或选址，也未写入数据库：

| 测试对象 | 经度 | 纬度 | 高度 |
| --- | --- | --- | --- |
| 起点 | 120.2082 | 30.2030 | 地面标记 |
| 终点 | 120.2110 | 30.2055 | 地面标记 |
| 测试飞行器 | 120.2101 | 30.2040 | 180 米 |

使用管理端现有任务流程创建/分配/执行仿真任务后，站点和航线才能按 Java 数据叠加。若地图来源给出的是 GCJ-02 或 BD-09，需先转换为 WGS84，不能直接混用。

## 替换成更大区域

1. 用新的 OSM 范围导出 GLB；保持 `mapProjection=MetricMapProjection`。
2. Java 17 在 Windows 导出时保留 `'-Dfile.encoding=UTF-8'`，确保 GLB JSON 中的中文有效。
3. 把新的 GLB 与配套 manifest 一起更新到 `public/models/hangzhou/`。manifest 的 `bbox` 填新区域，`origin` 必须逐项对应 GLB 的 `scenes[0].extras.origin`，不要自行用 bbox 中点代替。
4. 若更换文件名，修改 `useCityScene.ts` 中的 `modelName`，保持 GLB/manifest 的同名约定。
5. 构建并刷新页面，检查模型范围、相机和业务坐标。
6. 路灯使用当前源 OSM 的道路中心线。更换区域后，更新 `scripts/export_city_roads.py` 的源文件并运行脚本，重新生成 `binjiangRoads.ts`；不要把旧区域的装饰布局当作新区域实测数据。

## 仿真外观的实现与范围

2026-10-11，按用户选择先增强可交互仿真外观，真实精细模型后补：

- `cityAppearance.ts` 根据 GLB 的建筑属性识别建筑，共享三组窗格/玻璃材质；以世界坐标控制窗格尺寸，不修改几何。修复了 GLTFLoader 将建筑名称空格转为下划线后识别失败的问题。窗光、材质颜色、屋顶设备均是程序化装饰，没有真实外立面或室内开灯数据。
- 在源草地三角形上采样树木；在屋顶三角形上放置设备。树冠/树干、设备、路灯采用实例绘制，避免每个装饰单独增加 draw call。当前配置得到 158 棵树、117 个设备、136 盏路灯。
- `cityStreetDetails.ts` 沿源 OSM 道路中心线布置示意路灯，并避开建筑包围盒。路灯与树木的位置不是实测设施坐标。水体沿用原 GLB 轮廓，仅增加法线波纹；没有新增虚构的钱塘江河道。
- `citySymbols.ts` 绘制无人机符号、站点环形标记和具有像素宽度的动态虚线。DOM 信息卡显示业务对象编号、高度、电量。
- `useCityScene.ts` 增加环境反射、阴影、暮色泛光与色调映射；限制像素比为 1.5。退出时释放实例属性、几何、材质、原 GLB 贴图、环境贴图及后处理目标；迟到的模型加载结果会被释放。

参考图的宽河流、桥梁密集区域、完整城市天际线与照片级外观尚未实现。当前范围约 481 × 557 米，OSM 高度属性（部分 160/180 米）未做实测校核；增加窗格不会纠正底座的高度误差。扩展范围与替换精细 GLB 是后续数据工作，现有坐标链路可继续使用。

## 外观阶段验证

- `npm.cmd run build`：Vue 类型检查和生产构建通过；Vite 仍有大包体提示。
- `node --test tests/cityAppearance.test.mjs tests/cityCoordinates.test.mjs`：6 项通过。新增检查覆盖真实 GLTFLoader 名称清洗、建筑窗格材质应用、原始材质恢复与建筑几何/包围盒保持一致。
- 浏览器使用正式 AppHeader、FleetPanel、CityViewport 组件和隔离测试坐标验证暮色/日景/原始切换、近景/复位、范围外过滤、HTTP 503 → 重试恢复、延迟加载期间重新挂载。恢复后只有一个 canvas，成功渲染时无控制台 error；测试入口的 Vue Router 未匹配警告属于隔离页面。
- 截图：`docs/verification/binjiang-dusk-scene.png`、`binjiang-day-scene.png`。顶部明确标注隔离测试数据、未连接 Java，临时入口验证后删除。
- 1440 × 900、像素比 1 的隔离浏览器中，暮色一帧累计 388 次绘制、155901 个三角形（含阴影及后处理）、277 个几何、33 个纹理。最近 180 帧的 RAF 间隔 P50 约 6.2 ms、P95 约 7 ms；这不是 GPU 执行时间，也不能推断用户设备的帧率。原始模式首次显示会额外上传未使用过的原始贴图，重挂载后回到 33 个纹理；这些计数不等于 GPU 内存泄漏审计。
- 本阶段未连接真实 Java 任务流，未修改上海种子坐标，未修改原始 GLB 文件。管理端配置滨江坐标后仍需端到端验证真实业务对象。

## 验证与边界

2026-10-11 验证记录：

- `cd frontend; npm.cmd run build`：Vue 类型检查和 Vite 生产构建通过；已有大包体提示，不影响构建。
- `cd frontend; node --test tests/cityCoordinates.test.mjs`：5 项通过，覆盖原点/米制高度、东与北方向、范围过滤、无效配置、GLB 原点与内嵌贴图及源文件一致性。测试使用 Node 24 的 TypeScript 类型擦除能力。
- 浏览器在与正式页面相同的 App、路由和 CityViewport 中使用隔离测试数据验证：HTTP 503 错误提示 → 重试成功；GLB 建筑和测试航线渲染；上海坐标显示范围外提示；延迟加载期间切换页面后恢复成功且仅保留一个画布；复位视角可用。
- 截图见 `docs/verification/binjiang-glb-scene.png`。账号栏标注“测试数据”；该验证未连接 Java、未写数据库。临时验证入口在验证后删除。

此模型有 47 个源建筑/建筑部分对象，267 个 mesh，约 2 MB，25 个内嵌纹理（最大边 512 像素）；按 RGBA 加 mipmap 估算纹理占用约 27.5 MiB，不含几何和渲染目标。浏览器测得环境水平尺寸约 481 × 557 米。

这是 OSM 足迹、属性和默认规则生成的环境。尚未接入 DEM 高程、精确建筑外立面、地面高度采样、障碍物避碰或实机控制；测试航线显示成功不等于安全规划验证。当前模型原点高程为 0，Java 高度值直接按米绘制。

模型来源为 OpenStreetMap，保留 © OpenStreetMap contributors / ODbL 署名链接。后续替换素材也要同步维护来源及署名。
