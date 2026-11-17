"""Add clean previews to historical runs without overwriting evidence/reports."""
import json
import re
from PIL import Image
from river_yolo import ROOT, fingerprint
from patrol_eval import render
from patrol_io import replace_with_retry


def main():
    dataset = ROOT / 'data/haida-yolo'
    manifest_file = dataset / 'manifest.json'
    manifest_sha = fingerprint(manifest_file)
    records = {r['id']:r for r in json.loads(manifest_file.read_text(encoding='utf-8'))['records'] if r['split'] == 'test'}
    count = 0
    for report_file in (ROOT / 'runs/patrol').glob('*/report.json'):
        report = json.loads(report_file.read_text(encoding='utf-8'))
        if report.get('datasetSha256') != manifest_sha:
            raise ValueError('Historical dataset differs; preview not rewritten')
        destination = report_file.parent / 'preview'
        destination.mkdir(exist_ok=True)
        for row in report['rows']:
            identifier = row['id']
            if not re.fullmatch(r'data\d+(?:_DJI)?_\d+',identifier) or identifier not in records:
                raise ValueError('Unsafe or unrelated historical image')
            target = destination / f'{identifier}.jpg'
            if target.exists(): continue
            source = dataset / 'images/test' / f'{identifier}.jpg'
            if fingerprint(source) != records[identifier]['image_sha256']:
                raise ValueError('Historical source image changed')
            with Image.open(source) as image:
                pending = destination / f'{identifier}.pending.jpg'
                render(image,row['predictions'],pending,True)
                replace_with_retry(pending,target)
            count += 1
    print(f'CLEAN_HISTORICAL_PREVIEWS_CREATED {count}')


if __name__ == '__main__': main()
