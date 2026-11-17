# 模型与数据恢复

代码仓库与本机运行资源分开。没有上传 Python 虚拟环境、模型缓存、训练运行、HAIDA 全量数据、数据库、上传图片或录屏。三维运行资源和其来源说明随前端保存。

## YOLO

- 发布模型入口为 `ai/weights/patrol/model.json`，其中 `weights` 指向固定 SHA-256 命名的 `.pt` 文件。不能用官方 COCO 初始权重冒充项目漂浮物模型。
- 请求项目发布资源时，应取得模型文件、发布元数据、对应训练记录和数据清单；按元数据验证哈希后恢复到相对目录。现有本机代码包中的资源不因上传 GitHub 自动变为公网下载链接。
- `ai/scripts/vision_upload.py` 与 `patrol_eval.py` 会核对模型和数据。随机巡逻需要原 HAIDA 测试池及完整性记录；目前部分流程仍要求完整数据校验，精简图片包不保证直接运行。
- 自行重建环境、数据、训练和发布的步骤见 `ai/README.md`、`ai/env-spec.json`、`download_haida.py`、`prepare_dataset.py`、`river_yolo.py` 和 `pin_patrol_model.py`。训练需要单独算力与时间，不能将运行命令当作已复现结果。

## Agent

本地 Embedding 使用 `BAAI/bge-small-zh-v1.5`，按 `agent/README.md` 下载和校验。运行记录、知识索引及用户上传资料位于忽略的技术产物目录，新环境自行生成。DeepSeek Key 由运行者本机配置，不在代码仓库提供共享密钥。

## 影像来源

HAIDA 数据源为作者仓库 https://github.com/LiaoSteve/HAIDA-Trash-Dataset-High-Resolution-Aerial-image 。本项目使用港区/海岸航拍离线数据，不将其称为杭州现场拍摄。数据、模型与框架的许可分别核对，见根目录第三方说明。
