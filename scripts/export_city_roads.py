"""Export OSM road centrelines for illustrative street furniture. No third-party packages."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'assets-source/hangzhou/clipped/binjiang-test-500m.osm'
osm = ET.parse(source).getroot()
nodes = {node.attrib['id']: [float(node.attrib['lon']), float(node.attrib['lat'])] for node in osm.findall('node')}
roads = []
for way in osm.findall('way'):
    tags = {tag.attrib['k']: tag.attrib['v'] for tag in way.findall('tag')}
    if tags.get('highway') not in ('residential', 'service', 'tertiary', 'secondary', 'primary', 'footway', 'cycleway', 'path'):
        continue
    points = [nodes[ref.attrib['ref']] for ref in way.findall('nd') if ref.attrib['ref'] in nodes]
    if len(points) > 1:
        roads.append({'id': way.attrib['id'], 'kind': tags['highway'], 'bridge': tags.get('bridge') == 'yes', 'points': points})
target = ROOT / 'frontend/src/views/DigitalTwin/binjiangRoads.ts'
target.write_text('// Generated from the bundled OSM extract by scripts/export_city_roads.py.\n'
                  '// OSM road positions; street furniture added by the renderer is simulation detail.\n'
                  + 'export const binjiangRoads = ' + json.dumps(roads, ensure_ascii=False, separators=(',', ':')) + ' as const\n', encoding='utf-8')
print(f'Exported {len(roads)} road paths to {target}')
