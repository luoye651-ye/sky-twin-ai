import { readFile, stat } from 'node:fs/promises'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')
const assetPath = resolve(root, 'public/models/UAV/delivery_drone_gameready_free.glb')
const scenePath = resolve(root, 'src/views/DigitalTwin/useCityScene.ts')
const symbolsPath = resolve(root, 'src/views/DigitalTwin/citySymbols.ts')
const modelPath = resolve(root, 'src/views/DigitalTwin/aircraftModel.ts')

function check(condition, message) {
  if (!condition) throw new Error(message)
}

async function inspectGlb() {
  const bytes = await readFile(assetPath)
  check(bytes.toString('ascii', 0, 4) === 'glTF', 'UAV 文件不是有效的 GLB')
  check(bytes.readUInt32LE(4) === 2, 'UAV GLB 不是 glTF 2.0')
  check(bytes.readUInt32LE(8) === bytes.length, 'UAV GLB 声明长度与文件长度不一致')
  const jsonLength = bytes.readUInt32LE(12)
  const json = JSON.parse(bytes.toString('utf8', 20, 20 + jsonLength).trim())
  const nodeNames = new Set((json.nodes ?? []).map(node => node.name))
  for (const name of ['Main_Low', 'Box_Low', 'Screw_Low', 'Con_Low']) {
    check(nodeNames.has(name), `UAV GLB 缺少节点：${name}`)
  }
  check((json.meshes ?? []).length === 4, 'UAV GLB 网格数量发生变化')
  check((json.images ?? []).length === 4, 'UAV GLB 贴图数量发生变化')
  return bytes.length
}

const size = await stat(assetPath)
check(size.size > 0, 'public 中的 UAV GLB 是空文件')
const glbBytes = await inspectGlb()
const [sceneSource, symbolsSource, modelSource] = await Promise.all([
  readFile(scenePath, 'utf8'),
  readFile(symbolsPath, 'utf8'),
  readFile(modelPath, 'utf8'),
])

check(modelSource.includes('GLTFLoader'), '没有使用 GLTFLoader 加载 UAV 模型')
check(sceneSource.includes('loadAircraftModelAsset'), '场景没有加载 UAV GLB 资产')
check(sceneSource.includes('simulatedAircraft'), '场景没有标记范围外飞行器的仿真布点')
check(sceneSource.includes('simulationPosition'), '范围外飞行器没有可见的仿真位置')
check(!sceneSource.includes('createAircraftSymbol'), '场景仍在使用旧程序化无人机')
check(!symbolsSource.includes('export function createAircraftSymbol'), '旧程序化无人机实现仍然存在')

console.log(JSON.stringify({ passed: true, glbBytes, requiredNodes: 4, meshes: 4, images: 4 }, null, 2))
