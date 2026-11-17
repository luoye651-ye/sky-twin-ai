"""Prepare HAIDA VOC boxes for YOLO; group source sequences, never fake labels.

The Ningbo archive is retained/audited separately: it has no annotations and is
not part of this training set. HAIDA XML <filename> values predate the author's
renaming; pair XML/JPEG by matching file stem, and record that discrepancy.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import random
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile

from PIL import Image, ImageDraw
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
NAMES = ["garbage", "bottle"]
ARCHIVE_SHA = "64ed1b86fe0b5833e1c7b2385e623fc8eb4fb24f7fb6f9aea05acf46243fda6b"


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(4 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def safe_members(archive: zipfile.ZipFile) -> None:
    for info in archive.infolist():
        path = PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts or any(char in info.orig_filename for char in ("\\", ":", "\x00")):
            raise ValueError(f"Unsafe archive path: {info.filename}")
        if (info.external_attr >> 16) & 0o170000 == 0o120000:
            raise ValueError("Archive symlinks are not allowed")
        if not info.is_dir() and path.suffix.lower() not in (".jpg", ".xml"):
            raise ValueError(f"Unexpected archive entry: {info.filename}")


def parse_voc(path: Path, size: tuple[int, int]) -> tuple[list[list[float]], str]:
    raw = path.read_bytes()
    if len(raw) > 1_000_000 or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError(f"Unexpected XML content: {path}")
    tree = ET.fromstring(raw)
    if (int(tree.findtext("size/width", "0")), int(tree.findtext("size/height", "0"))) != size:
        raise ValueError(f"Image/XML dimension mismatch: {path}")
    width, height = size
    result = []
    for item in tree.findall("object"):
        label = item.findtext("name", "").strip()
        if label not in NAMES:
            raise ValueError(f"Unexpected class {label!r} in {path}")
        bounds = [float(item.findtext(f"bndbox/{key}", "nan")) for key in ("xmin", "ymin", "xmax", "ymax")]
        xmin, ymin, xmax, ymax = bounds
        if not all(math.isfinite(value) for value in bounds) or not (0 <= xmin < xmax <= width and 0 <= ymin < ymax <= height):
            raise ValueError(f"Out-of-image/empty bounding box: {path}: {bounds}")
        # Use the provided pixel rectangle consistently, no label invention or
        # silent clipping. VOC coordinates can touch right/bottom image edges.
        result.append([NAMES.index(label), (xmin + xmax) / (2 * width), (ymin + ymax) / (2 * height), (xmax - xmin) / width, (ymax - ymin) / height])
    return result, tree.findtext("filename", "")


class UnionFind:
    def __init__(self, keys):
        self.parents = {key: key for key in keys}

    def find(self, key):
        if self.parents[key] != key:
            self.parents[key] = self.find(self.parents[key])
        return self.parents[key]

    def union(self, left, right):
        left, right = self.find(left), self.find(right)
        if left != right:
            self.parents[max(left, right)] = min(left, right)


def source_group(stem: str) -> str:
    match = re.fullmatch(r"(data\d+)(?:_DJI)?_(\d+)", stem)
    if not match:
        raise ValueError(f"Unknown source-sequence naming: {stem}; do not randomly split frames")
    return match.group(1)


def split_groups(records: list[dict]) -> dict[str, str]:
    grouped = defaultdict(list)
    for record in records:
        grouped[record["group"]].append(record)
    groups = sorted(grouped)
    if len(groups) < 3:
        raise ValueError("Fewer than three independent source groups")
    # Choose reproducibly using group sizes and class-presence, never model/test
    # scores. A full group always belongs to exactly one split.
    rng = random.Random(42)
    best = None
    target = {"train": 0.7, "val": 0.2, "test": 0.1}
    for _ in range(3000):
        rng.shuffle(groups)
        mapping = {}
        counts = Counter()
        for group in groups:
            split = min(target, key=lambda key: (counts[key] / len(records) - target[key]) / target[key])
            mapping[group] = split
            counts[split] += len(grouped[group])
        presence = {split: set() for split in target}
        for group, items in grouped.items():
            for item in items:
                presence[mapping[group]].update(int(box[0]) for box in item["boxes"])
        if any(len(presence[split]) != len(NAMES) for split in target):
            continue
        score = sum((counts[split] / len(records) - target[split]) ** 2 for split in target)
        tie = tuple(sorted(mapping.items()))
        if best is None or (score, tie) < best[:2]:
            best = (score, tie, mapping.copy())
    if best is None:
        raise ValueError("Cannot make grouped train/val/test with both classes present")
    return best[2]


def audit_ningbo() -> None:
    path = ROOT / "data/raw/ningbo-v2/river-floating-debris-v2.zip"
    if path.exists():
        with zipfile.ZipFile(path) as archive:
            members = [info for info in archive.infolist() if not info.is_dir()]
            counts = Counter(PurePosixPath(info.filename).suffix.lower() for info in members)
        dump(path.parent / "archive-audit.json", {"actual_files": dict(counts), "can_train": False,
             "reason": "519 JPG only, no annotations; publisher v1 and v2 reference identical file ID/MD5. Not used for training.",
             "sha256": digest(path)})


def prepare() -> None:
    audit_ningbo()
    source = ROOT / "data/raw/haida"
    archive = source / "HAIDA.zip"
    proof = json.loads((source / "download-verification.json").read_text(encoding="utf-8"))
    actual = digest(archive)
    if actual != proof["sha256"] or (ARCHIVE_SHA and actual != ARCHIVE_SHA):
        raise ValueError("HAIDA archive checksum mismatch")
    with zipfile.ZipFile(archive) as zipped:
        safe_members(zipped)
    extracted = source / "extracted"
    if not extracted.exists():
        extracted.mkdir()
        tar = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/tar.exe"
        subprocess.run([str(tar), "-xf", str(archive), "-C", str(extracted)], check=True)
    images = {file.stem: file for file in extracted.rglob("*.jpg")}
    xmls = {file.stem: file for file in extracted.rglob("*.xml")}
    if len(images) != 1319 or images.keys() != xmls.keys():
        raise ValueError(f"Incomplete/unpaired HAIDA files: {len(images)} images, {len(xmls)} XML")
    records, thumbs = [], []
    for index, (stem, image_path) in enumerate(sorted(images.items())):
        with Image.open(image_path) as image:
            image.load()
            if image.getexif().get(274, 1) != 1:
                raise ValueError("Unexpected EXIF orientation; verify labels before rotating")
            boxes, declared = parse_voc(xmls[stem], image.size)
            small = np.asarray(image.convert("RGB").resize((32, 32)), dtype=np.int16)
            gray = np.asarray(image.convert("L").resize((9, 8)), dtype=np.int16)
            bits = (gray[:, 1:] > gray[:, :-1]).flatten()
            dhash = sum(int(bit) << bit_index for bit_index, bit in enumerate(bits))
            record = {"id": stem, "source_group": source_group(stem), "source_image": image_path.relative_to(source).as_posix(),
                      "source_xml": xmls[stem].relative_to(source).as_posix(), "xml_declared_filename": declared,
                      "size": list(image.size), "image_sha256": digest(image_path), "xml_sha256": digest(xmls[stem]),
                      "boxes": boxes, "dhash": f"{dhash:016x}"}
            records.append(record)
            thumbs.append(small)
        if index % 200 == 0:
            print(f"AUDIT {index + 1}/{len(images)}", flush=True)
    union = UnionFind({item["source_group"] for item in records})
    near_pairs = []
    for i, left in enumerate(records):
        for j in range(i):
            right = records[j]
            if left["source_group"] == right["source_group"]:
                continue
            exact = left["image_sha256"] == right["image_sha256"]
            close_hash = (int(left["dhash"], 16) ^ int(right["dhash"], 16)).bit_count() <= 4
            if exact or (close_hash and np.abs(thumbs[i] - thumbs[j]).mean() <= 3):
                union.union(left["source_group"], right["source_group"])
                near_pairs.append([left["id"], right["id"]])
    for item in records:
        item["group"] = union.find(item["source_group"])
    mapping = split_groups(records)
    for item in records:
        item["split"] = mapping[item["group"]]
    output = ROOT / "data/haida-yolo"
    manifest = {"dataset": "HAIDA", "source": proof, "classes": NAMES, "seed": 42,
                "grouping": "Author dataN sequence prefix; merge exact/near-duplicate groups (dHash<=4 AND RGB32 MAE<=3). No guaranteed physical flight/site identity.",
                "near_duplicate_pairs_merged": near_pairs, "group_to_split": mapping,
                "split_images": dict(Counter(item["split"] for item in records)),
                "split_boxes": {split: dict(Counter(NAMES[int(box[0])] for item in records if item["split"] == split for box in item["boxes"])) for split in ("train", "val", "test")},
                "negative_images": sum(not item["boxes"] for item in records),
                "scope": "Harbor/coastal aerial litter baseline; not Hangzhou/river field accuracy or item-by-item litter counting.",
                "records": records}
    if output.exists():
        old = output / "manifest.json"
        if not old.exists() or json.loads(old.read_text(encoding="utf-8")) != manifest:
            raise FileExistsError(f"Existing prepared data differs: {output}; preserve and inspect, no overwrite")
    else:
        output.mkdir(parents=True)
        for item in records:
            split = item["split"]
            dest_image = output / "images" / split / f"{item['id']}.jpg"
            dest_label = output / "labels" / split / f"{item['id']}.txt"
            dest_image.parent.mkdir(parents=True, exist_ok=True)
            dest_label.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(source / item["source_image"], dest_image)
            except OSError:
                shutil.copy2(source / item["source_image"], dest_image)
            dest_label.write_text("".join(f"{int(box[0])} " + " ".join(f"{value:.10f}" for value in box[1:]) + "\n" for box in item["boxes"]), encoding="utf-8")
        dump(output / "manifest.json", manifest)
    configuration = {"path": output.as_posix(), "train": "images/train", "val": "images/val", "test": "images/test", "names": dict(enumerate(NAMES))}
    (output / "data.yaml").write_text(yaml.safe_dump(configuration, sort_keys=False), encoding="utf-8")
    for split, limit in (("train", 12), ("val", 6)):
        candidates = sorted((item for item in records if item["split"] == split), key=lambda item: (not item["boxes"], item["id"]))[:limit]
        (output / f"smoke-{split}.txt").write_text("".join((output / "images" / split / f"{item['id']}.jpg").as_posix() + "\n" for item in candidates), encoding="utf-8")
    smoke = {**configuration, "train": "smoke-train.txt", "val": "smoke-val.txt"}
    smoke.pop("test")  # engineering smoke never touches the held-out test set
    (output / "smoke.yaml").write_text(yaml.safe_dump(smoke, sort_keys=False), encoding="utf-8")
    contact_sheet(records, source, output)
    verify(output)
    print("DATASET_PREPARED " + json.dumps({key: manifest[key] for key in ("dataset", "split_images", "split_boxes", "negative_images")}))


def contact_sheet(records: list[dict], source: Path, output: Path) -> None:
    selected = []
    for split in ("train", "val", "test"):
        groups = sorted({item["group"] for item in records if item["split"] == split})
        for group in groups[:4]:
            candidates = [item for item in records if item["group"] == group and item["split"] == split]
            selected.append(next((item for item in candidates if item["boxes"]), candidates[0]))
    canvas = Image.new("RGB", (1280, math.ceil(len(selected) / 4) * 208), "#12202c")
    draw = ImageDraw.Draw(canvas)
    for index, item in enumerate(selected):
        with Image.open(source / item["source_image"]) as image:
            tile = image.convert("RGB").resize((320, 180))
        pen = ImageDraw.Draw(tile)
        for cls, x, y, width, height in item["boxes"]:
            color = "#ffda22" if cls == 0 else "#ff55ee"
            pen.rectangle(((x - width / 2) * 320, (y - height / 2) * 180, (x + width / 2) * 320, (y + height / 2) * 180), outline=color, width=2)
        left, top = (index % 4) * 320, (index // 4) * 208
        canvas.paste(tile, (left, top))
        draw.text((left + 4, top + 182), f"{item['split']} / {item['id']}", fill="white")
    canvas.save(output / "annotation-contact-sheet.jpg")


def verify(output: Path) -> dict:
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    if manifest["classes"] != NAMES or manifest["source"]["sha256"] != ARCHIVE_SHA or len(manifest["records"]) != 1319:
        raise ValueError("Dataset identity/classes/count changed")
    canonical = {"path": output.as_posix(), "train": "images/train", "val": "images/val", "test": "images/test", "names": dict(enumerate(NAMES))}
    if yaml.safe_load((output / "data.yaml").read_text(encoding="utf-8")) != canonical:
        raise ValueError("data.yaml was changed; refusing unverified paths/splits/classes")
    smoke = {**canonical, "train": "smoke-train.txt", "val": "smoke-val.txt"}
    smoke.pop("test")
    if yaml.safe_load((output / "smoke.yaml").read_text(encoding="utf-8")) != smoke:
        raise ValueError("smoke.yaml was changed")
    for split, limit in (("train", 12), ("val", 6)):
        candidates = sorted((item for item in manifest["records"] if item["split"] == split), key=lambda item: (not item["boxes"], item["id"]))[:limit]
        expected = [(output / "images" / split / f"{item['id']}.jpg").as_posix() for item in candidates]
        if (output / f"smoke-{split}.txt").read_text(encoding="utf-8").splitlines() != expected:
            raise ValueError("Smoke subset changed or touched held-out data")
    seen, groups, sha_splits = set(), {}, {}
    counts, boxes = Counter(), Counter()
    for item in manifest["records"]:
        stem, split, group = item["id"], item["split"], item["group"]
        if stem in seen or (group in groups and groups[group] != split):
            raise ValueError("Duplicate image/group leakage")
        if item["image_sha256"] in sha_splits and sha_splits[item["image_sha256"]] != split:
            raise ValueError("Exact duplicate across splits")
        seen.add(stem)
        groups[group] = split
        sha_splits[item["image_sha256"]] = split
        image_path = output / "images" / split / f"{stem}.jpg"
        label_path = output / "labels" / split / f"{stem}.txt"
        if digest(image_path) != item["image_sha256"]:
            raise ValueError(f"Image changed/missing: {image_path}")
        lines = label_path.read_text(encoding="utf-8").splitlines()
        if len(lines) != len(item["boxes"]):
            raise ValueError("Missing/extra labels")
        for line, expected in zip(lines, item["boxes"]):
            actual = [float(value) for value in line.split()]
            if len(actual) != 5 or not all(math.isfinite(value) for value in actual) or actual[0] not in (0, 1):
                raise ValueError("Invalid YOLO label")
            if any(abs(left - right) > 1e-9 for left, right in zip(actual, expected)):
                raise ValueError("Label changed after conversion")
        counts[split] += 1
        boxes[split] += len(lines)
    for split in ("train", "val", "test"):
        if len(list((output / "images" / split).glob("*.jpg"))) != counts[split] or len(list((output / "labels" / split).glob("*.txt"))) != counts[split]:
            raise ValueError("Unexpected files in prepared dataset")
    if dict(counts) != manifest["split_images"] or not all(counts[split] and boxes[split] for split in ("train", "val", "test")):
        raise ValueError("Dataset split totals invalid")
    result = {"passed": True, "images": len(seen), "independent_groups": len(groups), "split_images": dict(counts), "split_boxes": dict(boxes), "manifest_sha256": digest(output / "manifest.json")}
    dump(ROOT / "logs/dataset-check.json", result)
    print("DATASET_VERIFIED " + json.dumps(result))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify"), default="prepare", nargs="?")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    else:
        verify(ROOT / "data/haida-yolo")
