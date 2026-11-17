import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js'
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js'
import { Line2 } from 'three/addons/lines/Line2.js'
import type { CityAppearance } from './cityAppearance'
import { loadAircraftModelAsset, type AircraftModelAsset, type AircraftModelInstance } from './aircraftModel'
import { createRegionScene } from './cityRegionScene'
import { parseCityRegion, type CityRegion } from './cityRegionData'
import { createRouteSymbol, createStationSymbol } from './citySymbols'
import type { Aircraft, Station, Task } from '../../../../shared/sky'
import { fromCityPosition, isInsideCity, toCityPosition, type CityModelManifest } from './cityCoordinates'
import { resolveAircraftDisplayAltitude } from './aircraftDisplay'
import type { AirspaceCheck, AirspaceZone } from '../../../../shared/airspace'
import { createAirspaceOverlay } from './airspaceOverlay'
import type { PositionSample } from '@sky/positioning'
import { createPositionOverlay } from './positionOverlay'
import type { RouteSketch, RouteWaypoint } from '@sky/routes'
import type { AirspacePoint } from '@sky/airspace'
import { createRouteDraftOverlay } from './routeDraftOverlay'
import { routePoint } from '../../utils/taskRoute'
import type { FlightNavigationDisplay } from '../../types/flightNavigation'
import { createFlightNavigationOverlay } from './flightNavigationOverlay'
import { moveOverlayChildren } from './sceneOverlay'
import { focusAircraftById } from './aircraftFocus'

export interface CitySceneStatus {
  phase: 'loading' | 'ready' | 'error'
  message: string
  outsideAircraft: number
  simulatedAircraft: number
  outsideStations: number
  navigationOutside?: boolean
}

export interface CityAircraftLabel {
  id: string
  altitude: number
  reportedAltitude: number
  battery: number
  x: number
  y: number
  simulated: boolean
  visualized: boolean
  positionSource?: string
  positionState?: string
}
export interface CityPlaceLabel { id: string; name: string; kind: 'place' | 'bridge' | 'station'; x: number; y: number }

const modelDirectory = `${import.meta.env.BASE_URL}models/hangzhou/`
const modelName = 'hangzhou-core-region'

// Each scene owns its GLB textures. Deduplicate shared materials, textures and geometries.
function releaseObject(object: THREE.Object3D) {
  const geometries = new Set<THREE.BufferGeometry>()
  const materials = new Set<THREE.Material>()
  const textures = new Set<THREE.Texture>()
  const bitmaps = new Set<ImageBitmap>()
  object.traverse(child => {
    if (!(child instanceof THREE.Mesh || child instanceof THREE.Line)) return
    if (child instanceof THREE.InstancedMesh) child.dispose()
    geometries.add(child.geometry)
    for (const material of Array.isArray(child.material) ? child.material : [child.material]) {
      materials.add(material)
      for (const value of Object.values(material)) {
        if (value instanceof THREE.Texture) {
          textures.add(value)
          if (typeof ImageBitmap !== 'undefined' && value.image instanceof ImageBitmap) bitmaps.add(value.image)
        }
      }
    }
  })
  geometries.forEach(value => value.dispose())
  materials.forEach(value => value.dispose())
  textures.forEach(value => value.dispose())
  bitmaps.forEach(value => value.close())
}

export function createCityScene(container: HTMLElement, onStatus: (status: CitySceneStatus) => void, onLabels?: (labels: CityAircraftLabel[], places: CityPlaceLabel[]) => void, onRoutePick?: (point: RouteWaypoint) => void) {
  const scene = new THREE.Scene()
  scene.background = new THREE.Color(0x152d43)
  const camera = new THREE.PerspectiveCamera(50, 1, 0.5, 10000)
  camera.position.set(500, 600, 700)
  const renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5))
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.info.autoReset = false
  const room = new RoomEnvironment()
  const pmrem = new THREE.PMREMGenerator(renderer)
  const environmentMap = pmrem.fromScene(room, 0.04)
  room.dispose(); pmrem.dispose()
  scene.environment = environmentMap.texture
  container.appendChild(renderer.domElement)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.maxPolarAngle = Math.PI / 2.1
  controls.minDistance = 20
  controls.maxDistance = 5000
  const hemisphere = new THREE.HemisphereLight(0x91baff, 0x344c58, 1.1)
  scene.add(hemisphere)
  const light = new THREE.DirectionalLight(0xffe2bc, 2.2)
  light.position.set(-300, 500, 300)
  light.castShadow = true
  light.shadow.mapSize.set(2048, 2048)
  light.shadow.camera.left = light.shadow.camera.bottom = -400
  light.shadow.camera.right = light.shadow.camera.top = 400
  light.shadow.camera.near = 1; light.shadow.camera.far = 1600
  light.shadow.bias = -0.0003; light.shadow.normalBias = 0.4
  scene.add(light)
  const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 }))
  const renderPass = new RenderPass(scene, camera)
  const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.25, 0.35, 1.1)
  const outputPass = new OutputPass()
  composer.addPass(renderPass); composer.addPass(bloom); composer.addPass(outputPass)

  const environment = new THREE.Group()
  const stationsGroup = new THREE.Group()
  const routesGroup = new THREE.Group()
  const airspaceGroup = new THREE.Group()
  const positionGroup = new THREE.Group()
  const draftGroup = new THREE.Group()
  const navigationGroup = new THREE.Group()
  scene.add(environment, stationsGroup, routesGroup, airspaceGroup, positionGroup, draftGroup, navigationGroup)
  const fleet = new Map<string, AircraftModelInstance & { simulated: boolean; displayAltitude: number; reportedAltitude: number; visualized: boolean }>()
  const targets = new Map<string, THREE.Vector3>()
  const timedFlights = new Map<string, { taskId: string; revision: number; points: AirspacePoint[]; rendered: number; target: number }>()
  const colors: Record<string, number> = { idle: 0x7b9eaf, assigned: 0xffc44a, flying: 0x37d9ff }
  let latest: { aircraft: Aircraft[]; stations: Station[]; tasks: Task[] } = { aircraft: [], stations: [], tasks: [] }
  let manifest: CityModelManifest | undefined
  let aircraftAsset: AircraftModelAsset | undefined
  let modelBounds: THREE.Box3 | undefined
  let appearance: Awaited<ReturnType<typeof createRegionScene>> | undefined
  let regionLabels: CityRegion['labels'] = []
  let appearanceMode: CityAppearance = 'dusk'
  let status: CitySceneStatus = { phase: 'loading', message: '正在加载杭州主城区与 UAV 模型…', outsideAircraft: 0, simulatedAircraft: 0, outsideStations: 0 }
  let disposed = false
  let generation = 0
  let manifestRequest: AbortController | undefined
  let overlaySignature = ''
  let airspaceSignature = ''
  let latestZones: AirspaceZone[] = []
  let latestCheck: AirspaceCheck | undefined
  let latestPositionTrack: PositionSample[] = []
  let positionSignature = ''
  let latestSketch: RouteSketch | undefined
  let latestNavigation: FlightNavigationDisplay | undefined
  let navigationSignature = '', navigationFocusId = ''
  let draftSignature = '', routeEditing = false
  let pointerDown: { x: number; y: number } | undefined
  function down(event: PointerEvent) { if (event.button === 0) pointerDown = { x: event.clientX, y: event.clientY } }
  function up(event: PointerEvent) {
    const start = pointerDown; pointerDown = undefined
    if (!routeEditing || !manifest || !latestSketch || !start || event.button !== 0 || Math.hypot(event.clientX - start.x, event.clientY - start.y) > 5) return
    const rect = renderer.domElement.getBoundingClientRect()
    const ray = new THREE.Raycaster(); ray.setFromCamera(new THREE.Vector2((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1), camera)
    const hit = ray.ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 1, 0), -(latestSketch.altitude - manifest.origin.ele)), new THREE.Vector3())
    if (!hit) return
    const point = fromCityPosition(hit.x, hit.z, manifest.origin)
    if (inside(point.longitude, point.latitude)) onRoutePick?.({ longitude: Number(point.longitude.toFixed(6)), latitude: Number(point.latitude.toFixed(6)) })
  }
  renderer.domElement.addEventListener('pointerdown', down); renderer.domElement.addEventListener('pointerup', up)

  function updateStatus(patch: Partial<CitySceneStatus>) {
    if (disposed) return
    status = { ...status, ...patch }
    onStatus(status)
  }
  function clear(group: THREE.Group) { releaseObject(group); group.clear() }
  function world(lon: number, lat: number, altitude = 0) {
    const position = toCityPosition(lon, lat, altitude, manifest!.origin)
    return new THREE.Vector3(position.x, position.y, position.z)
  }
  function inside(lon: number, lat: number) { return !!manifest && isInsideCity(lon, lat, manifest.bbox) }
  function simulationPosition(index: number, reportedAltitude: number) {
    const bridge = regionLabels.find(label => label.name === '复兴大桥')
    const center = bridge ? new THREE.Vector3(bridge.point[0], 0, bridge.point[1]) : world(120.1736, 30.2116)
    const firstPositions = [
      new THREE.Vector3(-620, 150, -260),
      new THREE.Vector3(-180, 210, 320),
      new THREE.Vector3(360, 175, -120),
      new THREE.Vector3(760, 240, 260),
    ]
    const offset = firstPositions[index] ?? new THREE.Vector3(
      Math.cos(index * 1.7) * (500 + index * 45),
      150 + index * 25,
      Math.sin(index * 1.7) * (500 + index * 45),
    )
    const position = center.add(offset)
    position.y = Math.max(position.y, Number.isFinite(reportedAltitude) ? reportedAltitude : 0)
    return position
  }
  function resetCamera() {
    if (!modelBounds || disposed) return
    const sphere = modelBounds.getBoundingSphere(new THREE.Sphere())
    const verticalFov = THREE.MathUtils.degToRad(camera.fov)
    const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * camera.aspect)
    const direction = new THREE.Vector3(0.7, 0.85, 1.1).normalize()
    const inverseView = new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().lookAt(direction, new THREE.Vector3(), camera.up)).invert()
    let distance = 0
    for (const x of [modelBounds.min.x, modelBounds.max.x]) for (const y of [modelBounds.min.y, modelBounds.max.y]) for (const z of [modelBounds.min.z, modelBounds.max.z]) {
      const corner = new THREE.Vector3(x, y, z).sub(sphere.center).applyQuaternion(inverseView)
      distance = Math.max(distance, corner.z + Math.abs(corner.y) / Math.tan(verticalFov / 2), corner.z + Math.abs(corner.x) / Math.tan(horizontalFov / 2))
    }
    distance *= 1.12
    controls.target.copy(sphere.center)
    camera.position.copy(sphere.center).addScaledVector(direction, distance)
    camera.far = Math.max(5000, distance * 5)
    camera.updateProjectionMatrix()
    controls.maxDistance = distance * 3
    controls.update()
  }

  function focusDistrict() {
    if (!manifest || disposed) return
    const center = world(120.19, 30.195)
    controls.target.copy(center)
    camera.position.copy(center).add(new THREE.Vector3(2400, 2600, 3300))
    controls.update()
  }

  function focusRiver() {
    if (!manifest || disposed) return
    const bridge = regionLabels.find(label => label.name === '复兴大桥')
    const center = bridge ? new THREE.Vector3(bridge.point[0], 0, bridge.point[1]) : world(120.1736, 30.2116)
    controls.target.copy(center)
    camera.position.copy(center).add(new THREE.Vector3(-1500, 1800, 2400))
    controls.update()
  }

  function setAppearance(mode: CityAppearance) {
    appearanceMode = mode
    appearance?.setMode(mode)
    const dusk = mode === 'dusk'
    scene.background = new THREE.Color(dusk ? 0x152d43 : 0x9bb5ca)
    scene.environmentIntensity = dusk ? 0.45 : 0.8
    hemisphere.intensity = dusk ? 0.65 : 1.6
    light.intensity = dusk ? 1.15 : 3
    light.color.setHex(dusk ? 0xffd5a2 : 0xfff2df)
    renderer.toneMappingExposure = dusk ? 1.05 : 1.2
    bloom.enabled = dusk
    if (scene.fog instanceof THREE.Fog) scene.fog.color.copy(scene.background)
  }

  function focusZone(id: string) {
    const zone = latestZones.find(value => value.id === id)
    if (!manifest || !zone || disposed) return
    const a = world(zone.west, zone.south), b = world(zone.east, zone.north)
    const center = a.clone().add(b).multiplyScalar(.5), distance = Math.max(900, a.distanceTo(b) * 1.25)
    controls.target.copy(center); camera.position.copy(center).add(new THREE.Vector3(-.5, .8, 1).multiplyScalar(distance)); controls.update()
  }
  function focusCheck() {
    if (!manifest || !latestCheck || disposed) return
    const bounds = new THREE.Box3().setFromPoints(latestCheck.route.map(point => world(point.longitude, point.latitude, point.altitude)))
    const center = bounds.getCenter(new THREE.Vector3()), distance = Math.max(1100, bounds.getSize(new THREE.Vector3()).length() * 1.2)
    controls.target.copy(center); camera.position.copy(center).add(new THREE.Vector3(-.5, .8, 1).multiplyScalar(distance)); controls.update()
  }
  function syncAirspace(zones: AirspaceZone[], check?: AirspaceCheck) {
    latestZones = zones; latestCheck = check
    if (!manifest || status.phase !== 'ready' || disposed) return
    const signature = JSON.stringify([zones, check])
    if (signature === airspaceSignature) return
    airspaceSignature = signature
    clear(airspaceGroup)
    const overlay = createAirspaceOverlay(zones, check, world, new THREE.Vector2(container.clientWidth, container.clientHeight))
    moveOverlayChildren(airspaceGroup, overlay)
  }
  function syncPositionTrack(points: PositionSample[]) {
    latestPositionTrack = points
    if (!manifest || status.phase !== 'ready' || disposed) return
    const signature = JSON.stringify(points.map(p => [p.id, p.sessionId, p.sampledAt, p.longitude, p.latitude, p.altitude]))
    if (signature === positionSignature) return
    positionSignature = signature; clear(positionGroup)
    // Do not relocate terminal points outside the model to fake in-range positions.
    const visible = points.map(p => inside(p.longitude, p.latitude) ? p : { ...p, accepted: false })
    const overlay = createPositionOverlay(visible, world, new THREE.Vector2(container.clientWidth, container.clientHeight))
    moveOverlayChildren(positionGroup, overlay)
  }
  function syncRouteDraft(sketch?: RouteSketch, editing = false) {
    latestSketch = sketch; routeEditing = editing
    renderer.domElement.style.cursor = editing ? 'crosshair' : ''
    if (!manifest || status.phase !== 'ready' || disposed) return
    const signature = JSON.stringify(sketch)
    if (signature === draftSignature) return
    draftSignature = signature; clear(draftGroup)
    if (sketch) { const overlay = createRouteDraftOverlay(sketch, world, new THREE.Vector2(container.clientWidth, container.clientHeight)); moveOverlayChildren(draftGroup, overlay) }
  }
  function focusRouteDraft() {
    if (!manifest || !latestSketch || disposed) return
    const bounds = new THREE.Box3().setFromPoints(latestSketch.points.map(p => world(p.longitude, p.latitude, p.altitude)))
    const center = bounds.getCenter(new THREE.Vector3()), distance = Math.max(900, bounds.getSize(new THREE.Vector3()).length() * 1.3)
    controls.target.copy(center); camera.position.copy(center).add(new THREE.Vector3(-.5, .8, 1).multiplyScalar(distance)); controls.update()
  }
  function focusPosition(lon: number, lat: number, altitude = 0) {
    if (!manifest || disposed || !inside(lon, lat)) return
    const center = world(lon, lat, altitude)
    controls.target.copy(center); camera.position.copy(center).add(new THREE.Vector3(-500, 650, 800)); controls.update()
  }
  function focusAircraft(id: string) {
    if (disposed || status.phase !== 'ready') return false
    return focusAircraftById(camera, controls, fleet, id)
  }

  function focusNavigation() {
    if (!manifest || !latestNavigation || disposed || !latestNavigation.points.every(p => inside(p.longitude, p.latitude))) return
    const bounds = new THREE.Box3().setFromPoints(latestNavigation.points.map(p => world(p.longitude, p.latitude, p.altitude)))
    const center = bounds.getCenter(new THREE.Vector3()), distance = Math.max(1200, bounds.getSize(new THREE.Vector3()).length() * 1.4)
    controls.target.copy(center); camera.position.copy(center).add(new THREE.Vector3(-.5, .8, 1).multiplyScalar(distance)); controls.update()
  }
  function syncNavigation(display?: FlightNavigationDisplay) {
    latestNavigation = display
    if (!manifest || status.phase !== 'ready' || disposed) return
    const signature = JSON.stringify(display)
    if (signature === navigationSignature) return
    navigationSignature = signature; clear(navigationGroup)
    const outside = !!display && !display.points.every(p => inside(p.longitude, p.latitude))
    if (!!status.navigationOutside !== outside) updateStatus({ navigationOutside: outside })
    if (display) navigationGroup.add(createFlightNavigationOverlay(display, world, new THREE.Vector2(container.clientWidth, container.clientHeight), inside))
    if (display && navigationFocusId !== display.taskId) { navigationFocusId = display.taskId; focusNavigation() }
    if (!display) navigationFocusId = ''
  }

  function sync(aircraft: Aircraft[], stations: Station[], tasks: Task[]) {
    latest = { aircraft, stations, tasks }
    if (!manifest || !aircraftAsset || status.phase !== 'ready' || disposed) return
    const positionedAircraft = aircraft.filter(a => Number.isFinite(a.altitude) && (!a.positionSource || a.positionSampledAt))
    const displayAircraft = positionedAircraft.filter(a => !a.positionSource || inside(a.longitude, a.latitude))
    const visibleStations = stations.filter(s => inside(s.longitude, s.latitude))
    const outsideAircraft = positionedAircraft.filter(a => !inside(a.longitude, a.latitude)).length
    const simulatedAircraft = displayAircraft.filter(a => !inside(a.longitude, a.latitude)).length
    const outsideStations = stations.length - visibleStations.length
    if (outsideAircraft !== status.outsideAircraft || simulatedAircraft !== status.simulatedAircraft || outsideStations !== status.outsideStations) {
      updateStatus({ outsideAircraft, simulatedAircraft, outsideStations })
    }
    const ids = new Set(displayAircraft.map(a => a.id))
    const visualSlotById = new Map([...ids].sort().map((id, index) => [id, index]))
    for (const [id, symbol] of fleet) {
      if (ids.has(id)) continue
      scene.remove(symbol.object); symbol.dispose(); fleet.delete(id); targets.delete(id); timedFlights.delete(id)
    }
    let simulatedIndex = 0
    for (const a of displayAircraft) {
      let symbol = fleet.get(a.id)
      const simulated = !inside(a.longitude, a.latitude)
      const flight = tasks.find(t => t.aircraftId === a.id && t.status === 'executing' && t.routePoints?.length && !a.positionSource && !simulated && t.routePoints.every(p => inside(p.longitude, p.latitude)))
      const altitude = a.positionSource || flight ? { displayAltitude: a.altitude, reportedAltitude: a.altitude, visualized: false } : resolveAircraftDisplayAltitude(a.altitude, visualSlotById.get(a.id) ?? 0)
      const position = simulated
        ? simulationPosition(simulatedIndex++, a.altitude)
        : world(a.longitude, a.latitude, altitude.displayAltitude)
      // Out-of-range coordinates already use explicit simulation positions.
      position.y = Math.max(position.y, simulated ? 120 : altitude.displayAltitude)
      if (!symbol) {
        symbol = { ...aircraftAsset.createInstance(a.type === 'evtol'), simulated, displayAltitude: position.y, reportedAltitude: altitude.reportedAltitude, visualized: !simulated && altitude.visualized }
        symbol.object.position.copy(position); fleet.set(a.id, symbol); scene.add(symbol.object)
      }
      symbol.simulated = simulated
      symbol.displayAltitude = position.y
      symbol.reportedAltitude = altitude.reportedAltitude
      symbol.visualized = !simulated && altitude.visualized
      // Sample-time replay and outage seeks must not acquire a second render-time interpolation.
      if (a.positionSource) symbol.object.position.copy(position)
      if (flight?.routePoints) {
        const old = timedFlights.get(a.id), elapsed = flight.elapsedSeconds ?? 0
        if (!old || old.taskId !== flight.id || old.revision !== flight.routeRevision) {
          timedFlights.set(a.id, { taskId: flight.id, revision: flight.routeRevision ?? 0, points: flight.routePoints, rendered: elapsed, target: elapsed }); symbol.object.position.copy(position)
        } else { old.target = elapsed; old.points = flight.routePoints }
      } else timedFlights.delete(a.id)
      symbol.beacon.color.setHex(colors[a.status] ?? 0x37d9ff).multiplyScalar(2)
      targets.set(a.id, position)
    }
    // Rebuild static overlays only when relevant fields change, not on every flight tick.
    const activeTasks = tasks.filter(t => ['assigned', 'executing'].includes(t.status) && Number.isFinite(t.cruiseAltitude))
    const signature = JSON.stringify([
      visibleStations.map(s => [s.id, s.longitude, s.latitude, s.status]),
      activeTasks.map(t => [t.id, t.startStationId, t.endStationId, t.cruiseAltitude, t.routeRevision, t.routePoints]),
    ])
    if (signature === overlaySignature) return
    overlaySignature = signature
    clear(stationsGroup); clear(routesGroup)
    for (const station of visibleStations) {
      const marker = createStationSymbol(station.status === 'enabled')
      marker.position.copy(world(station.longitude, station.latitude, 1)); stationsGroup.add(marker)
    }
    const stationById = new Map(visibleStations.map(s => [s.id, s]))
    for (const task of activeTasks) {
      const from = stationById.get(task.startStationId), to = stationById.get(task.endStationId)
      if (!from || !to) continue
      const points = task.routePoints?.length ? task.routePoints.map(p => world(p.longitude, p.latitude, p.altitude)) : [world(from.longitude, from.latitude, 1), world(from.longitude, from.latitude, task.cruiseAltitude), world(to.longitude, to.latitude, task.cruiseAltitude), world(to.longitude, to.latitude, 1)]
      routesGroup.add(createRouteSymbol(points, new THREE.Vector2(container.clientWidth, container.clientHeight)))
    }
  }

  async function loadModel() {
    if (disposed || status.phase === 'ready') return
    const token = ++generation
    manifestRequest?.abort()
    const request = new AbortController()
    manifestRequest = request
    updateStatus({ phase: 'loading', message: '正在加载杭州主城区与 UAV 模型…' })
    let created: Awaited<ReturnType<typeof createRegionScene>> | undefined
    let loadedAircraftAsset: AircraftModelAsset | undefined
    try {
      const [response, loadedAsset] = await Promise.all([
        fetch(`${modelDirectory}${modelName}.json`, { signal: request.signal }),
        loadAircraftModelAsset(request.signal),
      ])
      loadedAircraftAsset = loadedAsset
      if (!response.ok) throw new Error(`杭州主城区数据下载失败（HTTP ${response.status}）`)
      const config = parseCityRegion(await response.json())
      if (disposed || token !== generation) { loadedAircraftAsset.dispose(); return }
      updateStatus({ message: '正在构建杭州主城区 LOD、滨江细节与 UAV 实例…' })
      created = await createRegionScene(config, request.signal)
      if (disposed || token !== generation) { created.dispose(); releaseObject(created.model); loadedAircraftAsset.dispose(); return }
      const bounds = new THREE.Box3().setFromObject(created.model)
      manifest = { bbox: config.bbox, origin: config.origin, projection: config.projection }
      regionLabels = config.labels
      modelBounds = bounds
      appearance = created
      aircraftAsset = loadedAircraftAsset
      loadedAircraftAsset = undefined
      environment.add(created.model)
      const size = bounds.getSize(new THREE.Vector3())
      resetCamera(); focusRiver()
      const radius = bounds.getBoundingSphere(new THREE.Sphere()).radius
      scene.fog = new THREE.Fog(0x152d43, radius * .65, radius * 2)
      setAppearance(appearanceMode)
      updateStatus({ phase: 'ready', message: `${config.title} · ${(size.x / 1000).toFixed(1)} × ${(size.z / 1000).toFixed(1)} 公里 · ${config.buildings.length.toLocaleString()} 个建筑对象` })
      sync(latest.aircraft, latest.stations, latest.tasks)
      syncAirspace(latestZones, latestCheck)
      syncPositionTrack(latestPositionTrack)
      syncRouteDraft(latestSketch, routeEditing)
      syncNavigation(latestNavigation)
      if (latestCheck) focusCheck()
      else if (latestSketch) focusRouteDraft()
    } catch (error) {
      if (disposed || token !== generation) { if (created) { created.dispose(); releaseObject(created.model) }; return }
      loadedAircraftAsset?.dispose()
      created?.dispose()
      const wasAttached = created?.model.parent === environment
      clear(environment)
      if (created && !wasAttached) releaseObject(created.model)
      appearance = undefined
      updateStatus({ phase: 'error', message: error instanceof Error ? error.message : '建筑模型加载失败' })
    }
  }

  function resize() {
    const w = Math.max(1, container.clientWidth), h = Math.max(1, container.clientHeight)
    camera.aspect = w / h; camera.updateProjectionMatrix(); renderer.setSize(w, h)
    composer.setSize(w, h)
    routesGroup.children.forEach(child => { if (child instanceof Line2) child.material.resolution.set(w, h) })
    airspaceGroup.traverse(child => { if (child instanceof Line2) child.material.resolution.set(w, h) })
    positionGroup.traverse(child => { if (child instanceof Line2) child.material.resolution.set(w, h) })
    draftGroup.traverse(child => { if (child instanceof Line2) child.material.resolution.set(w, h) })
    navigationGroup.traverse(child => { if (child instanceof Line2) child.material.resolution.set(w, h) })
  }
  resize()
  const clock = new THREE.Clock()
  const projected = new THREE.Vector3()
  const frameTimes: number[] = []
  let elapsed = 0, lastLabels = 0, lastFrameAt = performance.now()
  let frame = 0
  function animate() {
    frame = requestAnimationFrame(animate)
    const delta = Math.min(clock.getDelta(), 0.1)
    elapsed += delta
    const now = performance.now()
    frameTimes.push(now - lastFrameAt); lastFrameAt = now
    if (frameTimes.length > 180) frameTimes.shift()
    const alpha = 1 - Math.exp(-3 * delta)
    for (const [id, symbol] of fleet) {
      const flight = timedFlights.get(id)
      if (flight) {
        flight.rendered += (flight.target - flight.rendered) * alpha
        const point = routePoint(flight.points, flight.rendered)
        if (point) symbol.object.position.copy(world(point.longitude, point.latitude, point.altitude))
      } else { const target = targets.get(id); if (target) symbol.object.position.lerp(target, alpha) }
    }
    appearance?.animate(elapsed)
    routesGroup.children.forEach(child => { if (child instanceof Line2) child.material.dashOffset = -elapsed * 8 })
    controls.update()
    // A kilometre-scale scene needs a near plane proportional to viewing distance.
    // Keeping the small-block 0.5m near plane makes co-planar river/ground layers flicker.
    const viewingDistance = camera.position.distanceTo(controls.target)
    const near = Math.max(1, viewingDistance / 250)
    if (Math.abs(camera.near - near) / near > .05) { camera.near = near; camera.updateProjectionMatrix() }
    if (scene.fog instanceof THREE.Fog) { scene.fog.near = Math.max(8000, viewingDistance * 1.1); scene.fog.far = Math.max(24000, viewingDistance + 26000) }
    renderer.info.reset()
    composer.render(delta)
    if (onLabels && manifest && now - lastLabels > 60) {
      lastLabels = now
      const labels: CityAircraftLabel[] = []
      // In city-wide overview, prioritize station geography; aircraft cards return when zooming in.
      if (viewingDistance < 30000) {
        for (const a of latest.aircraft) {
          const symbol = fleet.get(a.id)
          if (!symbol) continue
          projected.copy(symbol.object.position); projected.y += 8; projected.project(camera)
          if (projected.z < -1 || projected.z > 1 || Math.abs(projected.x) > 0.96 || Math.abs(projected.y) > 0.92) continue
          const y = (1 - projected.y) * container.clientHeight / 2
          if (y < 220) continue
          labels.push({ id: a.id, altitude: symbol.displayAltitude, reportedAltitude: symbol.reportedAltitude, battery: a.battery, x: (projected.x + 1) * container.clientWidth / 2, y, simulated: symbol.simulated, visualized: symbol.visualized, positionSource: a.positionSource, positionState: a.positionState })
        }
      }
      const places: CityPlaceLabel[] = []
      latestSketch?.waypoints.forEach((p, index) => {
        projected.copy(world(p.longitude, p.latitude, latestSketch!.altitude)).project(camera)
        if (projected.z >= -1 && projected.z <= 1 && Math.abs(projected.x) < .95 && Math.abs(projected.y) < .9) places.push({ id: `waypoint:${index}`, name: `${index === latestSketch!.selected ? '◉ ' : ''}航点 ${index + 1}`, kind: 'place', x: (projected.x + 1) * container.clientWidth / 2, y: (1 - projected.y) * container.clientHeight / 2 })
      })
      const stationLabelPositions: { x: number; y: number }[] = []
      for (const station of latest.stations) {
        if (!inside(station.longitude, station.latitude)) continue
        const position = world(station.longitude, station.latitude, 12)
        projected.copy(position).project(camera)
        if (projected.z < -1 || projected.z > 1 || Math.abs(projected.x) > .92 || Math.abs(projected.y) > .86) continue
        const base = { x: (projected.x + 1) * container.clientWidth / 2, y: (1 - projected.y) * container.clientHeight / 2 }
        const offsets = [[0, 0], [0, 42], [0, -42], [135, 0], [-135, 0], [115, 42], [-115, 42]]
        const candidate = offsets.map(([x, y]) => ({ x: base.x + x!, y: base.y + y! }))
          .find(value => !stationLabelPositions.some(other => Math.abs(value.x - other.x) < 145 && Math.abs(value.y - other.y) < 38)) ?? base
        stationLabelPositions.push(candidate)
        places.push({ id: station.id, name: station.name, kind: 'station', x: candidate.x, y: candidate.y })
      }
      for (const label of regionLabels) {
        if (!['bridge', 'place'].includes(label.kind)) continue
        projected.set(label.point[0], 30, label.point[1]).project(camera)
        if (projected.z < -1 || projected.z > 1 || Math.abs(projected.x) > .85 || Math.abs(projected.y) > .75) continue
        const x = (projected.x + 1) * container.clientWidth / 2, y = (1 - projected.y) * container.clientHeight / 2
        if (places.some(p => Math.hypot(x - p.x, y - p.y) < (p.kind === 'station' ? 130 : 100))) continue
        places.push({ id: `${label.kind}:${label.name}`, name: label.name, kind: label.kind === 'bridge' ? 'bridge' : 'place', x, y })
      }
      for (const zone of latestZones) {
        projected.copy(world((zone.west + zone.east) / 2, (zone.south + zone.north) / 2, zone.maxAltitude + 10)).project(camera)
        if (Math.abs(projected.x) > .9 || Math.abs(projected.y) > .85 || projected.z < -1 || projected.z > 1) continue
        const prefix = zone.type === 'no_fly' ? '禁飞' : `限高${zone.maxAltitude}m`
        places.push({ id: `airspace:${zone.id}`, name: `${prefix} · ${zone.name}${zone.activeNow ? '' : '（非生效）'}`, kind: 'place', x: (projected.x + 1) * container.clientWidth / 2, y: (1 - projected.y) * container.clientHeight / 2 })
      }
      onLabels(labels, places)
    }
  }
  animate()
  void loadModel()
  function dispose() {
    if (disposed) return
    disposed = true; generation++; manifestRequest?.abort()
    for (const symbol of fleet.values()) { scene.remove(symbol.object); symbol.dispose() }
    fleet.clear(); targets.clear(); timedFlights.clear()
    renderer.domElement.removeEventListener('pointerdown', down); renderer.domElement.removeEventListener('pointerup', up)
    appearance?.dispose()
    cancelAnimationFrame(frame); controls.dispose(); releaseObject(scene); scene.clear()
    aircraftAsset?.dispose(); aircraftAsset = undefined
    light.shadow.dispose(); environmentMap.dispose()
    bloom.dispose(); outputPass.dispose(); composer.dispose()
    renderer.dispose(); renderer.domElement.remove()
  }
  function getDiagnostics() {
    const times = [...frameTimes].sort((a, b) => a - b)
    const marker = navigationGroup.getObjectByName('navigation-current')
    return { navigationTaskId: latestNavigation?.taskId, navigationObjects: navigationGroup.children.flatMap(g => g.children.map(c => c.name)), navigationCurrent: marker?.position.toArray(), phase: status.phase, mode: appearanceMode, uavInstances: fleet.size, visualLiftedAircraft: [...fleet.values()].filter(symbol => symbol.visualized).length, aircraftDisplayAltitudes: Object.fromEntries([...fleet].map(([id, symbol]) => [id, symbol.displayAltitude])), stationInstances: stationsGroup.children.length, outsideAircraft: status.outsideAircraft, simulatedAircraft: status.simulatedAircraft, outsideStations: status.outsideStations, frameMsP50: times[Math.floor(times.length * 0.5)], frameMsP95: times[Math.floor(times.length * 0.95)], calls: renderer.info.render.calls, triangles: renderer.info.render.triangles, geometries: renderer.info.memory.geometries, textures: renderer.info.memory.textures, pixelRatio: renderer.getPixelRatio(), details: appearance?.counts }
  }
  return { sync, syncAirspace, syncPositionTrack, syncRouteDraft, syncNavigation, focusNavigation, focusRouteDraft, focusPosition, focusAircraft, focusZone, focusCheck, resize, resetCamera, focusDistrict, focusRiver, setAppearance, setTraffic: (visible: boolean) => appearance?.setTraffic(visible), retry: loadModel, getDiagnostics, dispose }
}
