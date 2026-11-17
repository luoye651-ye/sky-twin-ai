"""Build an offline metre-based Binjiang/river extract from OSM France Zhejiang PBF.

Python 3.11: pip install --target .runtime/geo-tools osmium==4.3.1 shapely==2.1.2
No invented footprints. Missing heights and bridge elevations are display assumptions.
"""
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.runtime/geo-tools'))
import osmium
from shapely.geometry import LineString, box
from shapely import wkb, make_valid

BBOX = [120.10, 30.10, 120.28, 30.29]
ORIGIN = {'lon': 120.19, 'lat': 30.215, 'ele': 0}
CLIP = box(*BBOX)
SCALE = 40075016.686 * math.cos(math.radians(ORIGIN['lat']))
def merc_y(lat):
    s = math.sin(math.radians(lat))
    return math.log((1 + s) / (1 - s)) / (4 * math.pi) + .5
def project(point):
    return [round((point[0] - ORIGIN['lon']) / 360 * SCALE, 1),
            round(-(merc_y(point[1]) - merc_y(ORIGIN['lat'])) * SCALE, 1)]
def number(value):
    match = re.match(r'^\s*(\d+(?:\.\d+)?)\s*(m|米)?\s*$', value or '')
    return float(match[1]) if match else None
def polygons(geometry):
    if geometry.is_empty:
        return []
    if geometry.geom_type == 'Polygon':
        return [geometry]
    return [p for g in getattr(geometry, 'geoms', []) for p in polygons(g)]
def rings(polygon):
    return [[project(p) for p in ring.coords[:-1]] for ring in [polygon.exterior, *polygon.interiors]]
def intersects_bounds(coords):
    xs, ys = zip(*coords)
    return max(xs) >= BBOX[0] and min(xs) <= BBOX[2] and max(ys) >= BBOX[1] and min(ys) <= BBOX[3]

class Extract(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.buildings, self.areas, self.roads, self.labels, self.boundary = [], [], [], [], []
        self.factory = osmium.geom.WKBFactory()
        self.errors = 0
        self.boundary_source_bounds = None
    def node(self, node):
        if not (BBOX[0] <= node.lon <= BBOX[2] and BBOX[1] <= node.lat <= BBOX[3]):
            return
        tags = dict(node.tags)
        if tags.get('place') in ('suburb', 'quarter') and tags.get('name'):
            self.labels.append({'name': tags['name'], 'kind': 'place', 'point': project([node.lon, node.lat])})
    def way(self, way):
        tags = dict(way.tags)
        kind = tags.get('highway')
        if kind not in ('motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'residential', 'service',
                        'motorway_link', 'trunk_link', 'primary_link', 'secondary_link', 'tertiary_link', 'unclassified', 'footway', 'cycleway'):
            return
        if tags.get('tunnel') == 'yes' or len(way.nodes) < 2 or any(not n.location.valid() for n in way.nodes):
            return
        coords = [(n.lon, n.lat) for n in way.nodes]
        if not intersects_bounds(coords):
            return
        line = LineString(coords).intersection(CLIP)
        parts = [line] if line.geom_type == 'LineString' else list(getattr(line, 'geoms', []))
        bridge = tags.get('bridge', 'no') not in ('no', 'false', '0')
        lanes = number(tags.get('lanes'))
        default = {'motorway': 16, 'trunk': 14, 'primary': 18, 'secondary': 14, 'tertiary': 10,
                   'residential': 7, 'service': 5, 'footway': 2.5, 'cycleway': 3}.get(kind, 7)
        width = min(42, max(2.5, number(tags.get('width')) or (lanes * 3.3 + 2 if lanes else default)))
        for part in parts:
            if part.geom_type != 'LineString' or part.length < .00004:
                continue
            points = [project(p) for p in part.simplify(.000004).coords]
            self.roads.append({'id': f'w{way.id}', 'kind': kind, 'name': tags.get('name', ''), 'width': width,
                               'bridge': bridge, 'height': 16 if bridge else .3, 'oneway': tags.get('oneway', 'no'), 'points': points})
            if bridge and tags.get('name') and ('桥' in tags['name']) and part.length > .003:
                self.labels.append({'name': tags['name'], 'kind': 'bridge', 'point': project(part.interpolate(.5, normalized=True).coords[0])})
    def area(self, area):
        tags = dict(area.tags)
        building = tags.get('building') not in (None, 'no')
        boundary = tags.get('boundary') == 'administrative' and tags.get('name') == '滨江区'
        water = tags.get('natural') == 'water' or tags.get('waterway') == 'riverbank'
        green = tags.get('landuse') in ('forest', 'grass', 'meadow', 'recreation_ground') or tags.get('natural') in ('wood', 'scrub') or tags.get('leisure') in ('park', 'garden', 'pitch')
        urban = tags.get('landuse') in ('residential', 'commercial', 'industrial', 'retail')
        if not (building or water or green or urban or boundary):
            return
        try:
            geom = wkb.loads(self.factory.create_multipolygon(area), hex=True)
            if not CLIP.intersects(geom):
                return
            if boundary:
                self.boundary_source_bounds = list(geom.bounds)
            geom = make_valid(geom).intersection(CLIP).simplify(.000003, preserve_topology=True)
            osm_id = ('w' if area.from_way() else 'r') + str(area.orig_id())
            for polygon in polygons(geom):
                if polygon.area < 1e-10:
                    continue
                shape = rings(polygon)
                if boundary:
                    self.boundary.append(shape)
                elif building:
                    height, levels = number(tags.get('height')), number(tags.get('building:levels'))
                    height_source = 'height' if height else 'levels' if levels else 'inferred'
                    defaults = {'apartments': 27, 'residential': 24, 'office': 36, 'commercial': 24, 'house': 9, 'industrial': 10, 'warehouse': 8, 'garage': 4, 'garages': 4}
                    height = height or (levels * 3.2 if levels else defaults.get(tags.get('building'), 18))
                    if not 1 <= height <= 800:
                        height, height_source = 18, 'inferred'
                    self.buildings.append({'id': osm_id, 'name': tags.get('name', ''), 'height': round(height, 1),
                                           'heightSource': height_source, 'rings': shape})
                else:
                    self.areas.append({'id': osm_id, 'kind': 'water' if water else 'green' if green else tags['landuse'],
                                       'name': tags.get('name', ''), 'rings': shape})
        except (RuntimeError, ValueError):
            self.errors += 1

if __name__ == '__main__':
    source = ROOT / 'assets-source/hangzhou/regional/zhejiang-20261009.osm.pbf'
    extract = Extract()
    print('Reading Zhejiang PBF and assembling areas...', flush=True)
    extract.apply_file(str(source), locations=True, idx='flex_mem')
    # Deduplicate the same named bridge's two carriageways for readable labels.
    labels = {}
    for label in extract.labels:
        labels.setdefault(label['name'], label)
    data = {'version': 1, 'projection': 'MetricMapProjection', 'origin': ORIGIN, 'bbox': BBOX,
            'title': '杭州滨江区 · 钱塘江两岸',
            'source': {'url': 'https://download.openstreetmap.fr/extracts/asia/china/zhejiang-latest.osm.pbf',
                       'fileLastModified': '2026-10-09T00:50:43Z', 'license': 'ODbL-1.0',
                       'attribution': '© OpenStreetMap contributors', 'errorsSkipped': extract.errors},
            'buildings': extract.buildings, 'areas': extract.areas, 'roads': extract.roads,
            'labels': list(labels.values()), 'districtBoundary': extract.boundary}
    data['districtSourceBounds'] = extract.boundary_source_bounds
    if not extract.boundary_source_bounds or not CLIP.covers(box(*extract.boundary_source_bounds)):
        raise RuntimeError('Crop must contain the entire source Binjiang administrative boundary')
    data['stats'] = {'buildings': len(extract.buildings), 'roads': len(extract.roads),
                     'areas': len(extract.areas), 'waterAreas': sum(a['kind'] == 'water' for a in extract.areas),
                     'bridgeSegments': sum(r['bridge'] for r in extract.roads),
                     'heightSources': dict(Counter(b['heightSource'] for b in extract.buildings))}
    output = ROOT / 'frontend/public/models/hangzhou/binjiang-region.json'
    temporary = output.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    temporary.replace(output)
    (ROOT / 'assets-source/hangzhou/regional/region-provenance.json').write_text(json.dumps({k: data[k] for k in ['source','bbox','origin','stats','districtSourceBounds']}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(data['stats'], ensure_ascii=False), flush=True)
    print(f'{output.stat().st_size / 1024 / 1024:.2f} MiB -> {output}', flush=True)
