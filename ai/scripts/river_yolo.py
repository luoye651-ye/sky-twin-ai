"""Local-only YOLOv8n training CLI. Never changes Java business/task state."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from importlib.metadata import version
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
(ROOT / ".ultralytics").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".ultralytics"))
for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(key, "4")
os.environ.setdefault("MPLBACKEND", "Agg")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def fingerprint(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def locked_versions() -> dict[str, str]:
    result = {}
    for line in (ROOT / "requirements-lock.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        name, expected = line.split("==", 1)
        actual = version(name)
        if actual != expected:
            raise RuntimeError(f"Dependency drift: {name}={actual}, expected {expected}; rerun setup.ps1")
        result[name] = actual
    return result


def check() -> None:
    installed = locked_versions()
    import torch
    import torchvision
    import ultralytics
    ultralytics.settings.update({"sync": False, "hub": False, "dvc": False, "raytune": False, "wandb": False, "mlflow": False, "comet": False, "clearml": False, "neptune": False, "tensorboard": False})
    from torchvision.ops import nms

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable. Install the specified CUDA PyTorch build; do not silently train on CPU.")
    torch.set_num_threads(4)
    torch.manual_seed(42)
    tensor = torch.randn(8, 8, device="cuda:0")
    product = tensor @ tensor
    torch.cuda.synchronize()
    if not torch.isfinite(product).all():
        raise RuntimeError("CUDA matrix kernel produced non-finite values")
    boxes = torch.tensor([[0., 0., 10., 10.], [1., 1., 9., 9.]], device="cuda:0")
    keep = nms(boxes, torch.tensor([0.9, 0.8], device="cuda:0"), 0.5)
    if keep.tolist() != [0]:
        raise RuntimeError("torchvision CUDA NMS witness failed")
    spec = json.loads((ROOT / "env-spec.json").read_text(encoding="utf-8"))
    versions = {"torch": torch.__version__, "torchvision": torchvision.__version__, "ultralytics": ultralytics.__version__}
    expected = {"torch": "2.8.0+cu128", "torchvision": "0.23.0+cu128", "ultralytics": "8.3.221"}
    if versions != expected:
        raise RuntimeError(f"Environment drift: {versions}; expected {expected}")
    proof = {"python": sys.version, "executable": sys.executable, "versions": versions,
             "device": torch.cuda.get_device_name(0), "shape": list(product.shape),
             "cuda_nms": keep.tolist(), "locked_packages": installed,
             "lock_sha256": fingerprint(ROOT / "requirements-lock.txt"),
             "spec_hash": hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:8]}
    write_json(ROOT / "logs/environment-check.json", proof)
    print("KERNEL_WITNESS " + json.dumps(proof), flush=True)


def stage() -> None:
    from ultralytics import YOLO, settings
    settings.update({"sync": False, "hub": False, "dvc": False, "raytune": False, "wandb": False, "mlflow": False, "comet": False, "clearml": False, "neptune": False, "tensorboard": False})
    path = ROOT / "weights/yolov8n.pt"
    path.parent.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(path))  # Ultralytics' official asset loader, not a third-party checkpoint.
    if model.task != "detect" or len(model.names) != 80:
        raise RuntimeError("Expected official COCO detection initializer with 80 classes")
    write_json(ROOT / "weights/initialization.json", {
        "source": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt",
        "bytes": path.stat().st_size, "sha256": fingerprint(path),
        "role": "COCO initializer, NOT a trained floating-debris detector", "classes": model.names,
    })
    print(f"INITIALIZER_STAGED {path} ({path.stat().st_size} bytes)")


def run(args: argparse.Namespace) -> None:
    installed = locked_versions()
    from ultralytics import YOLO, settings
    import torch
    settings.update({"sync": False, "hub": False, "dvc": False, "raytune": False, "wandb": False, "mlflow": False, "comet": False, "clearml": False, "neptune": False, "tensorboard": False})
    torch.set_num_threads(4)
    if args.device == "0" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; use --device cpu explicitly only if intended")
    data = (ROOT / "data/haida-yolo/data.yaml").resolve()
    if args.command == "smoke":
        data = (ROOT / "data/haida-yolo/smoke.yaml").resolve()
    if args.command != "predict" and not data.is_file():
        raise FileNotFoundError(f"Dataset not prepared: {data}; run prepare_dataset.py first")
    from prepare_dataset import verify, NAMES
    verify(ROOT / "data/haida-yolo")
    weights = Path(args.weights).resolve() if args.weights else ROOT / "weights/yolov8n.pt"
    if not weights.is_file():
        raise FileNotFoundError(f"Missing weights: {weights}. Run stage, or provide your trained best.pt.")
    if not args.weights and fingerprint(weights) != "f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36":
        raise ValueError("Official initializer changed; inspect the weight source before training")
    if args.command in ("val", "test", "predict") and not args.weights:
        raise ValueError("Evaluation/prediction requires explicit --weights pointing to YOUR trained best.pt")
    if args.command == "train" and args.resume and not args.weights:
        raise ValueError("Resume requires --weights pointing to the interrupted run's last.pt")
    name = args.name or f"{args.command}-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 1000000:06d}"
    if Path(name).name != name or name in (".", "..") or any(char in name for char in "/\\:"):
        raise ValueError("--name must be a single directory name")
    project = ROOT / "runs"
    if (project / name).exists() and not args.resume:
        raise FileExistsError(f"Run already exists: {project / name}; choose a new --name")
    run_record = {"command": args.command, "utc": datetime.now(timezone.utc).isoformat(), "arguments": vars(args),
                  "packages": installed, "lock_sha256": fingerprint(ROOT / "requirements-lock.txt"),
                  "initializer": str(weights), "weights_sha256": fingerprint(weights),
                  "data": str(data), "data_yaml_sha256": fingerprint(data) if data.exists() else None,
                  "dataset_manifest_sha256": fingerprint(ROOT / "data/haida-yolo/manifest.json"),
                  "note": "Smoke is engineering validation only, not final accuracy. Test is held-out; do not tune thresholds on test."}
    write_json(ROOT / f"logs/{name}-invocation.json", run_record)
    model = YOLO(str(weights))
    if args.command in ("val", "test", "predict") and list(model.names.values()) != NAMES:
        raise ValueError("Checkpoint classes differ from HAIDA; generic COCO weights are NOT this trained detector")
    common = dict(device=args.device, imgsz=args.imgsz, project=str(project), name=name, exist_ok=False, plots=True)
    if args.command in ("train", "smoke"):
        common.update(data=str(data), epochs=1 if args.command == "smoke" else args.epochs,
                      batch=2 if args.command == "smoke" else args.batch,
                      workers=args.workers, seed=42, deterministic=True, optimizer="SGD", lr0=0.01,
                      momentum=0.937, weight_decay=0.0005, patience=20, cache=False,
                      amp=False, close_mosaic=0 if args.command == "smoke" else 10,
                      save=True, save_period=10, resume=args.resume, pretrained=True)
        model.train(**common)
        result_path = Path(model.trainer.save_dir)
        if not (result_path / "weights/best.pt").is_file() or not (result_path / "results.csv").is_file():
            raise RuntimeError("Training returned without checkpoint/results.csv")
        run_record["output"] = str(result_path)
        run_record["best_sha256"] = fingerprint(result_path / "weights/best.pt")
        print(f"TRAIN_FINISHED {result_path}")
    elif args.command in ("val", "test"):
        result = model.val(data=str(data), split=args.command, batch=args.batch, workers=args.workers,
                           conf=0.001, iou=0.7, **common)
        run_record["metrics"] = result.results_dict
        run_record["speed_ms"] = result.speed
        run_record["output"] = str(result.save_dir)
        write_json(Path(result.save_dir) / "evaluation.json", run_record)
        print("EVALUATION_FINISHED " + json.dumps(result.results_dict))
    else:
        if not args.source:
            raise ValueError("predict requires --source <image-or-directory>")
        if not Path(args.source).exists():
            raise FileNotFoundError(args.source)
        count = 0
        for result in model.predict(source=args.source, conf=args.conf, save=True, save_txt=True, save_conf=True, stream=True, **common):
            count += 1
        run_record["images_processed"] = count
        run_record["output"] = str(model.predictor.save_dir)
        print(f"PREDICT_FINISHED {count} inputs; {model.predictor.save_dir}")
    run_record["completed"] = True
    write_json(ROOT / f"logs/{name}-invocation.json", run_record)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "stage", "smoke", "train", "val", "test", "predict"))
    parser.add_argument("--weights", help="Trusted local checkpoint; val/test/predict must specify trained best.pt")
    parser.add_argument("--device", choices=("0", "cpu"), default="0")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--name")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--source")
    parser.add_argument("--conf", type=float, default=0.25)
    args = parser.parse_args()
    if min(args.epochs, args.imgsz, args.batch) <= 0 or args.workers < 0 or not 0 <= args.conf <= 1:
        parser.error("epochs/imgsz/batch must be positive, workers nonnegative, conf in [0,1]")
    if args.resume and args.command != "train":
        parser.error("--resume is only valid for train")
    if args.command == "check":
        check()
    elif args.command == "stage":
        stage()
    else:
        run(args)


if __name__ == "__main__":
    main()  # Windows multiprocessing guard; workers=0 is the conservative baseline.
