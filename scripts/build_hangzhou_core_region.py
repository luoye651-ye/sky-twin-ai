"""Build an offline Hangzhou urban-core LOD scene from the local Zhejiang OSM PBF.

The Binjiang/river box keeps full detail. Outside it, representative buildings and
major roads are retained so a city-wide overview remains usable in a browser.
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
from shapely import make_valid, wkb

BBOX = [119.90, 29.90, 120.65, 30.60]
DETAIL_BBOX = [120.10, 30.10, 120.28, 30.29]
ORIGIN = {'lon': 120.275, 'lat': 30.25, 'ele': 0}
CLIP, DETAIL_CLIP = box(*BBOX), box(*DETAIL_BBOX)
MAX_BUILDINGS, MAX_ROADS, MAX_AREAS = 48000, 36000, 9000
MAJOR_ROADS = {'motorway', 'trunk', 'primary', 'secondary', 'tertiary',
               'motorway_link', 'trunk_link', 'primary_link', 'secondary_link', 'tertiary_link'}
ALL_DETAIL_ROADS = MAJOR_ROADS | {'residential', 'service', 'unclassified', 'footway', 'cycleway'}
SCALE = 40075016.686 * math.cos(math.radians(ORIGIN['lat']))


def merc_y(lat):
    value = math.sin(math.radians(lat))
    return math.log((1 + value) / (1 - value)) / (4 * math.pi) + .5


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
    return [polygon for item in getattr(geometry, 'geoms', []) for polygon in polygons(item)]


def rings(polygon, tolerance):
    simplified = polygon.simplify(tolerance, preserve_topology=True)
    return [[project(point) for point in ring.coords[:-1]]
            for ring in [simplified.exterior, *simplified.interiors]
            if len(ring.coords) >= 4]


def intersects(bounds, coords):
    xs, ys = zip(*coords)
    return max(xs) >= bounds[0] and min(xs) <= bounds[2] and max(ys) >= bounds[1] and min(ys) <= bounds[3]


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
        if tags.get('place') in ('city', 'town', 'suburb', 'quarter') and tags.get('name'):
            self.labels.append({'name': tags['name'], 'kind': 'place', 'point': project([node.lon, node.lat])})

    def way(self, way):
        tags = dict(way.tags)
        kind = tags.get('highway')
        if kind not in ALL_DETAIL_ROADS or tags.get('tunnel') == 'yes' or len(way.nodes) < 2:
            return
        if any(not node.location.valid() for node in way.nodes):
            return
        coords = [(node.lon, node.lat) for node in way.nodes]
        if not intersects(BBOX, coords):
            return
        detailed = intersects(DETAIL_BBOX, coords)
        if not detailed and kind not in MAJOR_ROADS:
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
            points = [project(point) for point in part.simplify(.000004 if detailed else .00002).coords]
            self.roads.append({'id': f'w{way.id}', 'kind': kind, 'name': tags.get('name', ''), 'width': width,
                               'bridge': bridge, 'height': 16 if bridge else .3,
                               'oneway': tags.get('oneway', 'no'), 'points': points,
                               '_score': 1000 if detailed else 200 + (50 if tags.get('name') else 0)})
            if bridge and tags.get('name') and '桥' in tags['name'] and part.length > .003:
                self.labels.append({'name': tags['name'], 'kind': 'bridge',
                                    'point': project(part.interpolate(.5, normalized=True).coords[0])})

    def area(self, area):
        tags = dict(area.tags)
        building = tags.get('building') not in (None, 'no')
        boundary = tags.get('boundary') == 'administrative' and tags.get('name') == '滨江区'
        water = tags.get('natural') == 'water' or tags.get('waterway') == 'riverbank'
        green = (tags.get('landuse') in ('forest', 'grass', 'meadow', 'recreation_ground')
                 or tags.get('natural') in ('wood', 'scrub')
                 or tags.get('leisure') in ('park', 'garden', 'pitch'))
        urban = tags.get('landuse') in ('residential', 'commercial', 'industrial', 'retail')
        if not (building or water or green or urban or boundary):
            return
        try:
            geometry = wkb.loads(self.factory.create_multipolygon(area), hex=True)
            if not CLIP.intersects(geometry):
                return
            if boundary:
                self.boundary_source_bounds = list(geometry.bounds)
            geometry = make_valid(geometry).intersection(CLIP)
            osm_id = ('w' if area.from_way() else 'r') + str(area.orig_id())
            for polygon in polygons(geometry):
                if polygon.area < 1e-10:
                    continue
                detailed = DETAIL_CLIP.contains(polygon.representative_point())
                if boundary:
                    shape = rings(polygon, .000003)
                    if shape:
                        self.boundary.append(shape)
                    continue
                if building:
                    height, levels = number(tags.get('height')), number(tags.get('building:levels'))
                    explicit = bool(height or levels)
                    # Outside Binjiang, retain landmark/large buildings plus a stable sample.
                    if not detailed and not (tags.get('name') or explicit or polygon.area >= 1.2e-7 or abs(area.orig_id()) % 6 == 0):
                        continue
                    shape = rings(polygon, .000003 if detailed else .000012)
                    if not shape:
                        continue
                    height_source = 'height' if height else 'levels' if levels else 'inferred'
                    defaults = {'apartments': 27, 'residential': 24, 'office': 36, 'commercial': 24,
                                'house': 9, 'industrial': 10, 'warehouse': 8, 'garage': 4, 'garages': 4}
                    height = height or (levels * 3.2 if levels else defaults.get(tags.get('building'), 18))
                    if not 1 <= height <= 800:
                        height, height_source = 18, 'inferred'
                    score = (1000 if detailed else 0) + (250 if explicit else 0) + (120 if tags.get('name') else 0) + min(100, polygon.area * 1e8)
                    self.buildings.append({'id': osm_id, 'name': tags.get('name', ''), 'height': round(height, 1),
                                           'heightSource': height_source, 'rings': shape, '_score': score})
                else:
                    if not detailed and urban and polygon.area < 2e-6:
                        continue
                    shape = rings(polygon, .000004 if detailed else .000025)
                    if not shape:
                        continue
                    score = (1000 if detailed else 0) + (500 if water else 200 if green else 50) + min(100, polygon.area * 1e7)
                    self.areas.append({'id': osm_id, 'kind': 'water' if water else 'green' if green else tags['landuse'],
                                       'name': tags.get('name', ''), 'rings': shape, '_score': score})
        except (RuntimeError, ValueError):
            self.errors += 1


def trim(items, maximum):
    items.sort(key=lambda item: (-item.pop('_score'), item['id']))
    return items[:maximum]


if __name__ == '__main__':
    source = ROOT / 'assets-source/hangzhou/regional/zhejiang-20261009.osm.pbf'
    extract = Extract()
    print('Reading Zhejiang PBF and assembling Hangzhou urban-core LOD...', flush=True)
    extract.apply_file(str(source), locations=True, idx='flex_mem')
    candidate_counts = {'buildings': len(extract.buildings), 'roads': len(extract.roads), 'areas': len(extract.areas)}
    extract.buildings = trim(extract.buildings, MAX_BUILDINGS)
    extract.roads = trim(extract.roads, MAX_ROADS)
    extract.areas = trim(extract.areas, MAX_AREAS)
    labels = {}
    for label in extract.labels:
        labels.setdefault(f"{label['kind']}:{label['name']}", label)
    data = {
        'version': 1, 'projection': 'MetricMapProjection', 'origin': ORIGIN, 'bbox': BBOX,
        'detailBbox': DETAIL_BBOX, 'title': '杭州主城区 · 滨江数字孪生',
        'source': {
            'url': 'https://download.openstreetmap.fr/extracts/asia/china/zhejiang-latest.osm.pbf',
            'fileLastModified': '2026-10-09T00:50:43Z', 'license': 'ODbL-1.0',
            'attribution': '© OpenStreetMap contributors', 'errorsSkipped': extract.errors,
            'lod': '滨江全细节；主城区外围保留主要道路、地表与代表性建筑',
        },
        'buildings': extract.buildings, 'areas': extract.areas, 'roads': extract.roads,
        'labels': list(labels.values()), 'districtBoundary': extract.boundary,
        'districtSourceBounds': extract.boundary_source_bounds,
    }
    if not extract.boundary_source_bounds or not CLIP.covers(box(*extract.boundary_source_bounds)):
        raise RuntimeError('City crop must contain the entire source Binjiang administrative boundary')
    data['stats'] = {
        'buildings': len(extract.buildings), 'roads': len(extract.roads), 'areas': len(extract.areas),
        'waterAreas': sum(item['kind'] == 'water' for item in extract.areas),
        'bridgeSegments': sum(item['bridge'] for item in extract.roads),
        'heightSources': dict(Counter(item['heightSource'] for item in extract.buildings)),
        'candidateCounts': candidate_counts,
    }
    output = ROOT / 'frontend/public/models/hangzhou/hangzhou-core-region.json'
    temporary = output.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    temporary.replace(output)
    provenance = ROOT / 'assets-source/hangzhou/regional/hangzhou-core-provenance.json'
    provenance.write_text(json.dumps({key: data[key] for key in ['source', 'bbox', 'detailBbox', 'origin', 'stats', 'districtSourceBounds']}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(data['stats'], ensure_ascii=False), flush=True)
    print(f'{output.stat().st_size / 1024 / 1024:.2f} MiB -> {output}', flush=True)
