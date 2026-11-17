# 航拍漂浮垃圾 YOLOv8n 本地基线

本目录仅负责模型实验；不维护任务、订单或事件状态，也尚未接入平台的“环境发现”界面。Java 仍是业务状态唯一来源。

## 数据选择与边界

按用户后续选择，正式基线改用 **HAIDA** 航拍水面垃圾数据。作者提供的公开压缩包实际包含 1,319 张 JPG 和 1,319 份 Pascal VOC XML，类别为 `garbage`（漂浮垃圾/垃圾区域）、`bottle`（瓶子）。不能把垃圾区域框当作逐件垃圾数量，也不是五类宁波数据。

- 作者入口：<https://github.com/LiaoSteve/HAIDA-Trash-Dataset-High-Resolution-Aerial-image/tree/HAIDA-trash-dataset>
- 公开文件 ID：`12ieYe9479Yee9eYADrGal6CYKxg2lwG_`。
- 原始包 979,276,090 bytes（约 934 MiB），SHA-256：`64ed1b86fe0b5833e1c7b2385e623fc8eb4fb24f7fb6f9aea05acf46243fda6b`。
- 数据来自港区/沿海水面航拍，不是杭州河道。后续需要另采、另标杭州等河道影像做外部验证。
- 保留作者引用：Y. H. Liao and J. G. Juang, *Application of Unmanned Aerial Vehicles for Marine Trash Detection and Real-Time Monitoring System*, NTOU, 2021。
- 作者仓库显示 MIT 许可；数据分发范围与训练框架许可分别核对，不把仓库许可当成整个产品的许可。Ultralytics 官方提供 AGPL-3.0 / Enterprise 许可：<https://docs.ultralytics.com/models/yolov8/>。

此前宁波数据完整下载并通过发布者 MD5，但公开 v1/v2 都是同一份 ZIP，**实际只有 519 张 JPG、没有标注**，不能训练。保留在 `data/raw/ningbo-v2/`，不混入 HAIDA。下载说明与实际包不一致，不能再称其为“已下载840张带标注数据”。

## 目录

```text
ai/
  .venv/                       独立 Python 环境，不改项目原 .venv / conda base
  env-spec.json                声明式环境规格
  requirements-lock.txt        本机验证的依赖锁
  data/raw/haida/               原始包、下载来源、校验记录、只读用途原图/XML
  data/raw/ningbo-v2/           不可直接训练的原宁波包与审计
  data/haida-yolo/              images、labels、data.yaml、smoke.yaml、manifest.json
  weights/yolov8n.pt            官方 COCO 初始权重，不是漂浮物训练成果
  runs/<实验名>/                best.pt / last.pt / results.csv / args.yaml / 曲线
  logs/                        环境、数据校验、每次调用参数与哈希
  scripts/                     下载、转换、训练、验证脚本
```

数据、权重、虚拟环境、训练产物已在 `ai/.gitignore` 排除。YOLO 格式图片使用原图硬链接以节省空间；**不要编辑这些图片**，因为会影响原图链接，训练前的 SHA-256 检查会拒绝篡改后的数据。

## 已安装环境

Windows x64，Python 3.13，PyTorch 2.8.0+cu128，torchvision 0.23.0+cu128，Ultralytics 8.3.221。本机是 RTX 4060 Ti 16GB。固定单 GPU、`workers=0` 适配 Windows；不安装 CUDA Toolkit、不改显卡驱动。

以下命令均在 PowerShell、项目根目录执行，不需要先激活虚拟环境：

```powershell
Set-Location C:\path\to\sky-twin
.\ai\.venv\Scripts\python.exe ai\scripts\river_yolo.py check
.\ai\.venv\Scripts\python.exe ai\scripts\prepare_dataset.py verify
.\ai\.venv\Scripts\python.exe ai\scripts\test_dataset_tools.py
```

`KERNEL_WITNESS` 必须包含 CUDA 矩阵计算、CUDA NMS 通过与准确依赖版本；仅 `import torch` 不代表 GPU 可用。

## 正式训练

```powershell
.\ai\.venv\Scripts\python.exe ai\scripts\river_yolo.py train --name haida-yolov8n-baseline --epochs 100 --imgsz 640 --batch 8
```

默认 seed=42，SGD，lr0=0.01，patience=20，workers=0，cache=False，amp=False（避免 AMP 自检自动下载另一个模型；此小模型先用 FP32 验证）。训练使用 `train`，每轮仅用 `val` 选择最佳 checkpoint，**不在训练过程中跑 test**。100 是最大轮数，早停可能提前结束；不承诺训练时长或准确率。

输出权重：

```text
ai/runs/haida-yolov8n-baseline/weights/best.pt
ai/runs/haida-yolov8n-baseline/weights/last.pt
```

同名实验目录已存在时拒绝覆盖，请换 `--name`。显存不足时换新实验名并将 `--batch 8` 调为 `--batch 4`；不会自动改变实验配置。训练时请保留终端，Ctrl+C 可中断；正常完成或中断后的状态以 `last.pt` 实际是否保存为准。

中断续训（只用于尚未达到设定轮数的训练，参数以 checkpoint 为准）：

```powershell
.\ai\.venv\Scripts\python.exe ai\scripts\river_yolo.py train --resume --weights ai\runs\haida-yolov8n-baseline\weights\last.pt
```

## 验证、最终测试与图片预测

调参阶段只跑验证集：

```powershell
.\ai\.venv\Scripts\python.exe ai\scripts\river_yolo.py val --weights ai\runs\haida-yolov8n-baseline\weights\best.pt
```

定稿后再跑一次保留测试集：

```powershell
.\ai\.venv\Scripts\python.exe ai\scripts\river_yolo.py test --weights ai\runs\haida-yolov8n-baseline\weights\best.pt
```

输出 `evaluation.json`、Precision、Recall、mAP50、mAP50-95、曲线与混淆矩阵。测试集不能拿来选模型、训练轮数或阈值；与论文结果不直接比较，因为我们重新按组划分。

预测你自己的图片或文件夹（换成真实存在的本机路径）：

```powershell
.\ai\.venv\Scripts\python.exe ai\scripts\river_yolo.py predict --weights ai\runs\haida-yolov8n-baseline\weights\best.pt --source D:\path\to\your-image.jpg
```

预测图和 YOLO 文本输出在单独实验目录。原始 COCO `ai/weights/yolov8n.pt` 不能当作漂浮物训练权重用于上述测试/预测，脚本会检查类别并拒绝。

## 工程冒烟，不代表正式训练

```powershell
.\ai\.venv\Scripts\python.exe ai\scripts\river_yolo.py smoke --name haida-smoke --imgsz 640
.\ai\.venv\Scripts\python.exe ai\scripts\river_yolo.py val --weights ai\runs\haida-smoke\weights\best.pt --name haida-smoke-val
```

冒烟只用训练集的12张、验证集的6张训练1轮，不接触保留 test。随后 `val` 命令检查完整验证集的评测入口。**低分/零分也不是故障，不能将冒烟权重的分数当最终识别能力。** 再次执行冒烟需换名；正式训练仍从官方初始权重开始，不接着冒烟权重训练。

## 数据审计与防泄漏

- XML 必须与 JPG 同名配对；拒绝缺失标签、未知类别、尺寸不一致、非有限/越界/空框。XML 明确无 object 才作为负样本，绝不把“丢失标注文件”当负样本。
- XML 的旧 `<filename>` 与作者重命名后的文件不一致，保留在 manifest 中；配对以同名 XML/JPG 为准，并用带框联系表抽检。
- 同一 `dataN` 序列不跨集合；跨序列的精确重复/明显近重复先合并组，再固定 seed=42 选择约70/20/10划分；逐张保存源文件哈希和划分，非逐帧随机切分。
- `dataN` 是文件名前缀，不等同于经核验的独立物理航次/地点；近重复过滤是启发式检查，不能保证没有所有形式的相似场景。仍需外部河道测试。
- `manifest.json`、`annotation-contact-sheet.jpg`、`logs/dataset-check.json` 提供本次实际数量和抽检依据。每次 train/val/test 前复核图片与标签哈希/数值，发现更改即停止。

本次固定划分实际为：train **922张/4616框**，val **265张/1669框**，test **132张/136框**；共456张 XML明确无目标的负样本。两个类别分布不均，val中的瓶子只有18框、test只有12框，单类分数不稳定，不能据此宣称生产可用。共10个文件名前缀组，未将相邻同组帧随机打散。

## 重新部署（当前电脑无需重复下载）

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ai\scripts\setup.ps1
.\ai\.venv\Scripts\python.exe ai\scripts\download_haida.py
.\ai\.venv\Scripts\python.exe ai\scripts\prepare_dataset.py prepare
.\ai\.venv\Scripts\python.exe ai\scripts\river_yolo.py stage
.\ai\.venv\Scripts\python.exe ai\scripts\river_yolo.py check
```

HAIDA 是 PPMd ZIP（压缩方法98），Python 标准 `zipfile` 无法解压；下载器用 Windows 自带 `tar.exe` 完整读取校验，转换器安全检查路径后再解压。中断/损坏文件会保留，不会覆盖原始数据；如解压中断形成不完整目录，需要先检查该目录，不能直接删整个 `ai/data`。

## 学习点

检测器是网络结构；初始权重是迁移学习起点；标注数据告诉模型“哪里是什么”；`best.pt` 才是训练后候选模型。下一小步：训练完成后，先读 `results.csv` 中验证集指标，再决定是否进行最终 test。未因环境已生成而认定用户已掌握训练与评测。

## 页面演示：AI水域巡逻离线评测

主导航「环境发现」或 `http://127.0.0.1:5173/environment`：每次新巡逻随机抽取1～132张不重复的HAIDA test图片进行真实推理，同次巡逻刷新保持结果不变。展示图片/检出数量列表，点击后在当前页无标题弹窗查看无英文横幅检测图。页面不展示评测指标、报告下载或列表下方详情；后台保留来源及原始可追溯结果，随机子集结果不能替代完整test精度。旧AI巡逻地址自动跳转。无需重新标注；不是杭州实拍或真实飞行，不自动生成应急事件。

训练完成后运行 `ai/scripts/pin_patrol_model.py --run haida-demo-to100` 发布已完成权重。缺失模型时界面明确禁用启动，不使用中间权重或伪造框。完整部署、口径、权限与验收见 [AI_PATROL_EVALUATION_V1.md](../docs/AI_PATROL_EVALUATION_V1.md)。
