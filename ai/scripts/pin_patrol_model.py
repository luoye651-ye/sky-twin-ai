"""Freeze a COMPLETED training run for the patrol demo; never pick by test score."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
from river_yolo import ROOT, fingerprint, write_json
from patrol_io import replace_with_retry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    if Path(args.run).name != args.run or args.run in (".", "..") or any(c in args.run for c in "/\\:"):
        raise ValueError("Use a single local training run name")
    record = json.loads((ROOT / "logs" / f"{args.run}-invocation.json").read_text(encoding="utf-8"))
    if not record.get("completed") or record.get("command") != "train":
        raise ValueError("Training is not finished; no intermediate checkpoint may be published")
    source = ROOT / "runs" / args.run / "weights/best.pt"
    sha = fingerprint(source)
    if sha != record["best_sha256"]:
        raise ValueError("Checkpoint differs from the completed training record")
    folder = ROOT / "weights/patrol"
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"{sha}.pt"
    if destination.exists():
        if fingerprint(destination) != sha:
            raise ValueError("Published checkpoint was changed")
    else:
        shutil.copyfile(source, destination)
    manifest = ROOT / "data/haida-yolo/manifest.json"
    data_sha = fingerprint(manifest)
    if data_sha != record["dataset_manifest_sha256"]:
        raise ValueError("Dataset changed since training")
    value = {"modelName": args.run, "modelSha256": sha, "datasetSha256": data_sha,
             "weights": f"weights/patrol/{sha}.pt", "dataset": "HAIDA", "split": "test", "imageCount": 132,
             "imgsz": 640, "confidence": 0.25, "matchIou": 0.5, "nmsIou": 0.7,
             "scope": "仿真巡逻 / HAIDA 港区航拍离线评测；非杭州实拍、非影像自动定位、非真实飞行"}
    staged = folder / "model.pending.json"
    write_json(staged, value)
    replace_with_retry(staged, folder / "model.json")
    print("PATROL_MODEL_PINNED " + json.dumps(value, ensure_ascii=False))


if __name__ == "__main__":
    main()
