"""Fixed single-upload inference. Java stores evidence/state; no training or network."""
import argparse
import json
import math
from pathlib import Path
import uuid

from river_yolo import ROOT, fingerprint, locked_versions, write_json
from patrol_eval import computation_lock


def normalized_box(xyxy, width, height):
    x1, y1, x2, y2 = (float(value) for value in xyxy)
    if not all(math.isfinite(value) for value in (x1, y1, x2, y2)):
        raise ValueError('Non-finite prediction')
    x1, x2 = max(0, x1), min(width, x2)
    y1, y2 = max(0, y1), min(height, y2)
    if x2 <= x1 or y2 <= y1:
        raise ValueError('Empty prediction')
    return dict(x=x1/width, y=y1/height, width=(x2-x1)/width, height=(y2-y1)/height)


def compute(analysis_id, expected_model, expected_image):
    if str(uuid.UUID(analysis_id)) != analysis_id:
        raise ValueError('Invalid analysis id')
    locked_versions()
    directory = ROOT / 'runs/vision' / analysis_id
    image_path = directory / 'input.image'
    config = json.loads((ROOT / 'weights/patrol/model.json').read_text(encoding='utf-8'))
    weights = ROOT / 'weights/patrol' / (expected_model + '.pt')
    if config['modelSha256'] != expected_model or fingerprint(weights) != expected_model or fingerprint(image_path) != expected_image:
        raise ValueError('Evidence or published model changed')
    from PIL import Image
    from ultralytics import YOLO
    import torch
    with Image.open(image_path) as source:
        image = source.convert('RGB')
    if image.width > 4096 or image.height > 4096 or image.width * image.height > 12_000_000:
        raise ValueError('Image too large')
    device = 0 if torch.cuda.is_available() else 'cpu'
    result = YOLO(str(weights)).predict(source=image, imgsz=640, conf=.25, iou=.7,
        max_det=100, device=device, verbose=False)[0]
    predictions = []
    for box, category, confidence in zip(result.boxes.xyxy.cpu().tolist(), result.boxes.cls.cpu().tolist(), result.boxes.conf.cpu().tolist()):
        category = int(category)
        if category not in (0, 1):
            raise ValueError('Unexpected class')
        predictions.append(dict(**normalized_box(box, image.width, image.height),
            label=('garbage', 'bottle')[category], confidence=confidence))
    # Recheck bytes after inference, so a concurrently changed file cannot be attributed to this result.
    if fingerprint(image_path) != expected_image or fingerprint(weights) != expected_model:
        raise ValueError('Evidence changed during inference')
    write_json(directory / 'result.json', dict(analysisId=analysis_id, imageSha256=expected_image,
        modelSha256=expected_model, width=image.width, height=image.height, confidenceThreshold=.25,
        device=str(device), predictions=predictions))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', required=True)
    parser.add_argument('--model-sha', required=True)
    parser.add_argument('--image-sha', required=True)
    args = parser.parse_args()
    with computation_lock():
        compute(args.id, args.model_sha, args.image_sha)
