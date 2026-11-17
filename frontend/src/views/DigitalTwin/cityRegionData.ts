import { parseCityManifest, type CityModelManifest } from './cityCoordinates.ts'

export type MapPoint = [number, number]
export type MapRings = MapPoint[][]
export interface RegionBuilding { id: string; name: string; height: number; heightSource: 'height' | 'levels' | 'inferred'; rings: MapRings }
export interface RegionRoad { id: string; name: string; kind: string; width: number; height: number; bridge: boolean; oneway: string; points: MapPoint[] }
export interface CityRegion extends CityModelManifest {
  version: 1
  title: string
  detailBbox?: [number, number, number, number]
  source: { url: string; fileLastModified: string; license: string; attribution: string; lod?: string }
  buildings: RegionBuilding[]
  areas: { id: string; kind: string; name: string; rings: MapRings }[]
  roads: RegionRoad[]
  labels: { name: string; kind: string; point: MapPoint }[]
  districtBoundary: MapRings[]
  districtSourceBounds: [number, number, number, number]
  stats: { buildings: number; roads: number; waterAreas: number; bridgeSegments: number; heightSources: Record<string, number>; candidateCounts?: Record<string, number> }
}
export function parseCityRegion(value: unknown): CityRegion {
  parseCityManifest(value)
  const data = value as CityRegion
  const points = (v: unknown, min: number): v is MapPoint[] => Array.isArray(v) && v.length >= min && v.length < 200000 && v.every(p => Array.isArray(p) && p.length === 2 && p.every(n => Number.isFinite(n) && Math.abs(n) < 100000))
  const rings = (v: unknown): v is MapRings => Array.isArray(v) && v.length > 0 && v.every(r => points(r, 3))
  if (data.version !== 1 || !data.source?.url || !Array.isArray(data.buildings) || data.buildings.length > 50000
    || !Array.isArray(data.areas) || data.areas.length > 10000 || !Array.isArray(data.roads) || data.roads.length > 50000
    || !data.buildings.every(b => b.id && Number.isFinite(b.height) && b.height > 0 && b.height <= 800 && ['height','levels','inferred'].includes(b.heightSource) && rings(b.rings))
    || !data.areas.every(a => ['water','green','residential','commercial','industrial','retail'].includes(a.kind) && rings(a.rings))
    || !data.roads.every(r => points(r.points, 2) && Number.isFinite(r.width) && r.width >= 1 && r.width <= 60 && Number.isFinite(r.height))
    || !Array.isArray(data.labels) || !data.labels.every(l => typeof l.name === 'string' && points([l.point], 1))
    || !Array.isArray(data.districtBoundary) || !data.districtBoundary.every(rings)
    || (data.detailBbox !== undefined && (!Array.isArray(data.detailBbox) || data.detailBbox.length !== 4 || !data.detailBbox.every(Number.isFinite)
      || data.detailBbox[0] < data.bbox[0] || data.detailBbox[1] < data.bbox[1] || data.detailBbox[2] > data.bbox[2] || data.detailBbox[3] > data.bbox[3]))
    || !Array.isArray(data.districtSourceBounds) || data.districtSourceBounds.length !== 4 || !data.districtSourceBounds.every(Number.isFinite)
    || data.districtSourceBounds[0] < data.bbox[0] || data.districtSourceBounds[1] < data.bbox[1]
    || data.districtSourceBounds[2] > data.bbox[2] || data.districtSourceBounds[3] > data.bbox[3]) {
    throw new Error('滨江区域数据无效：需要有效的建筑、道路和水体几何')
  }
  return data
}
