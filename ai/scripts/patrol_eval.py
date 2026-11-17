"""One bounded Python computation job; Java alone owns job/business state.

Random subset of the fixed HAIDA test image pool and published weights. No network services, no
training, no arbitrary file/dataset/threshold arguments. Results stay local.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import re
import time
import uuid

from river_yolo import ROOT, fingerprint, locked_versions, write_json
from prepare_dataset import verify, NAMES
from patrol_metrics import match, ratio
from patrol_io import replace_with_retry
from patrol_sample import select_records


@contextmanager
def computation_lock():
    import msvcrt
    folder = ROOT / ".runtime"
    folder.mkdir(exist_ok=True)
    with (folder / "patrol.lock").open("a+b") as handle:
        if handle.seek(0, 2) == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise RuntimeError("Another evaluator is still computing; retry after it exits") from error
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def render(image, boxes, destination, prediction):
    from PIL import ImageDraw, ImageFont
    canvas = image.convert("RGB")
    canvas.thumbnail((1280, 960))
    sx, sy = canvas.width / image.width, canvas.height / image.height
    pen = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(ROOT / ".ultralytics/Ultralytics/Arial.ttf"), 17)
    for item in boxes:
        x, y, width, height = item["box"]
        rect = (x * sx, y * sy, (x + width) * sx, (y + height) * sy)
        color = "#ffce40" if prediction else "#35eead"
        pen.rectangle(rect, outline=color, width=3)
        label = NAMES[item["classId"]] + (f" {item['confidence']:.2f}" if prediction else " GT")
        tx, ty = min(rect[0], max(0, canvas.width - 160)), max(0, rect[1] - 22)
        pen.rectangle((tx, ty, tx + 160, ty + 22), fill="#081b2d")
        pen.text((tx + 2, ty), label, font=font, fill=color)
    if not boxes:
        pen.text((10, 35), "No detections at conf >= 0.25" if prediction else "No annotated targets", font=font, fill="white")
    canvas.save(destination, "JPEG", quality=88)


def compute(run_id, expected_sha, image_count):
    locked_versions()
    config = json.loads((ROOT / "weights/patrol/model.json").read_text(encoding="utf-8"))
    if config["modelSha256"] != expected_sha:
        raise ValueError("Published model changed before job launch; restart explicitly")
    if config["confidence"] != .25 or config["imgsz"] != 640 or config["matchIou"] != .5 or config["nmsIou"] != .7 or config["split"] != "test":
        raise ValueError("Fixed evaluation protocol was modified")
    weights = ROOT / "weights/patrol" / f"{expected_sha}.pt"
    if fingerprint(weights) != expected_sha:
        raise ValueError("Published model hash mismatch")
    output = ROOT / "runs/patrol" / run_id
    output.mkdir(parents=True, exist_ok=False)
    def progress(stage, processed):
        temporary = output / "progress.pending.json"
        write_json(temporary, {"stage": stage, "processed": processed, "total": image_count})
        replace_with_retry(temporary, output / "progress.json")
    progress("verifying", 0)
    dataset = ROOT / "data/haida-yolo"
    verify(dataset)
    if fingerprint(dataset / "manifest.json") != config["datasetSha256"]:
        raise ValueError("Published dataset hash mismatch")
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    records = sorted((item for item in manifest["records"] if item["split"] == "test"), key=lambda item: item["id"])
    if len(records) != 132:
        raise ValueError("Expected exactly 132 held-out test images")
    records = select_records(records, image_count, run_id)
    # A dedicated list makes the validator actually process only this run's sample.
    import yaml
    selected_list = output / 'selected-images.txt'
    selected_list.write_text('\n'.join((dataset / 'images/test' / f"{item['id']}.jpg").as_posix() for item in records) + '\n', encoding='utf-8')
    selected_data = yaml.safe_load((dataset / 'data.yaml').read_text(encoding='utf-8'))
    selected_data['test'] = selected_list.as_posix()
    selected_yaml = output / 'selected-data.yaml'
    selected_yaml.write_text(yaml.safe_dump(selected_data, allow_unicode=True), encoding='utf-8')
    # Import only after deterministic/provenance checks; no remote logging.
    from ultralytics import YOLO, settings
    import torch
    from PIL import Image
    settings.update({key: False for key in ("sync", "hub", "dvc", "raytune", "wandb", "mlflow", "comet", "clearml", "neptune", "tensorboard")})
    torch.set_num_threads(4)
    if not torch.cuda.is_available():
        raise RuntimeError("Configured CUDA GPU is not available")
    model = YOLO(str(weights))
    if list(model.names.values()) != NAMES:
        raise ValueError("Wrong checkpoint classes")
    progress("evaluating", 0)
    started = time.perf_counter()
    validation_output = {}
    def batch_done(validator):
        progress("evaluating", min(image_count, int(validator.seen)))
    def validation_done(validator):
        validation_output["predictions"] = validator.jdict
    model.add_callback("on_val_batch_end", batch_done)
    model.add_callback("on_val_end", validation_done)
    result = model.val(data=str(selected_yaml), split="test", imgsz=640, batch=8,
                       device=0, workers=0, conf=.001, iou=.7, max_det=300,
                       plots=False, save_json=True, project=str(output), name="metrics", exist_ok=False,
                       verbose=False)
    elapsed = time.perf_counter() - started
    # This Ultralytics version keeps the validator local to val(), not on model.
    predictions = validation_output["predictions"]  # Same pass as mAP; empty is valid.
    by_image = defaultdict(list)
    valid_ids = {item["id"] for item in records}
    for item in predictions:
        image_id = str(item["image_id"])
        if image_id not in valid_ids or item["category_id"] not in (1, 2):
            raise ValueError("Unexpected validator image or class mapping")
        if item["score"] >= .25:
            by_image[image_id].append({"classId": item["category_id"] - 1, "confidence": item["score"], "box": item["bbox"]})
    for kind in ("predicted", "truth", "original"):
        (output / kind).mkdir()
    rows = []
    for index, item in enumerate(records):
        identifier = item["id"]
        if not re.fullmatch(r"data\d+(?:_DJI)?_\d+", identifier):
            raise ValueError("Unsafe image identifier")
        width, height = item["size"]
        truths = [{"classId": int(c), "box": [(x-w/2)*width, (y-h/2)*height, w*width, h*height]} for c,x,y,w,h in item["boxes"]]
        matched = match(by_image[identifier], truths)
        with Image.open(dataset / "images/test" / f"{identifier}.jpg") as image:
            render(image, matched["predictions"], output / "predicted" / f"{identifier}.jpg", True)
            render(image, truths, output / "truth" / f"{identifier}.jpg", False)
            original = image.convert("RGB")
            original.thumbnail((1280, 960))
            original.save(output / "original" / f"{identifier}.jpg", "JPEG", quality=88)
        rows.append({"id": identifier, "filename": f"{identifier}.jpg", **matched, "truths": truths,
                     "status": "missed" if matched["fn"] else "false_positive" if matched["fp"] else "correct"})
        progress("rendering", index + 1)
    tp, fp, fn = (sum(item[key] for item in rows) for key in ("tp", "fp", "fn"))
    metrics = result.results_dict
    report = {"protocolVersion": "haida-patrol-random-v2", "runId": run_id, "modelName": config["modelName"], "modelSha256": expected_sha,
              "poolImageCount": 132, "samplingSeed": run_id, "samplingStrategy": "uniform-count-without-replacement",
              "datasetSha256": config["datasetSha256"], "dataset": "HAIDA", "split": "test", "classes": NAMES,
              "scope": config["scope"], "imageCount": len(rows), "imgsz": 640, "confidence": .25, "matchIou": .5,
              "mapConfidenceFloor": .001, "nmsIou": .7, "maxDet": 300, "tp": tp, "fp": fp, "fn": fn,
              "precision": ratio(tp, tp+fp), "recall": ratio(tp, tp+fn),
              "map50": metrics["metrics/mAP50(B)"], "map5095": metrics["metrics/mAP50-95(B)"],
              "speedMs": result.speed, "evaluationSeconds": elapsed,
              "metricNotes": "Precision/Recall: fixed conf0.25, class-aware confidence-order 1:1 IoU>=0.5; mAP: Ultralytics 8.3.221 conf floor0.001. Confidence is not accuracy. Undefined ratios=null. Repeated runs are not independent test samples.",
              "rows": rows}
    if not all(math.isfinite(float(report[key])) for key in ("map50", "map5095", "evaluationSeconds")):
        raise RuntimeError("Non-finite evaluation metrics")
    write_json(output / "report.json", report)
    progress("completed", image_count)
    print("PATROL_EVALUATION_COMPLETE", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model-sha", required=True)
    parser.add_argument("--image-count", required=True, type=int, choices=range(1,133))
    args = parser.parse_args()
    if str(uuid.UUID(args.run_id)) != args.run_id or not re.fullmatch("[a-f0-9]{64}", args.model_sha):
        raise ValueError("Invalid run/model identifier")
    with computation_lock():
        compute(args.run_id, args.model_sha, args.image_count)
