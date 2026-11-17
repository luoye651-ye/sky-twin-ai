import { aircraftTypes, stationTypes, taskTypes, type Snapshot } from '../../../shared/sky.ts'

export interface ChartDatum { key: string; label: string; value: number; color: string }
const palette = ['#37d9ff', '#3f8cff', '#35e6b2', '#ffc45b', '#a58bff', '#ff708e', '#8aabc3']

function distribution<T>(rows: T[], field: (row: T) => string, labels: Record<string, string>): ChartDatum[] {
  const counts = new Map(Object.keys(labels).map(key => [key, 0]))
  for (const row of rows) {
    const key = field(row)
    counts.set(key, (counts.get(key) ?? 0) + 1)
  }
  return [...counts].map(([key, value], index) => ({ key, label: labels[key] ?? `其他（${key}）`, value, color: palette[index % palette.length]! }))
}

/** Read-only projections of the Java snapshot, never a second business state. */
export function buildOverviewMetrics(snapshot: Snapshot) {
  const fleet = distribution(snapshot.aircraft, a => a.status, { idle: '空闲', assigned: '已分配', flying: '飞行中', charging: '充电中', maintenance: '维护停用', fault: '故障停用' })
  const fleetTypes = distribution(snapshot.aircraft, a => a.type, aircraftTypes)
  const taskKinds = distribution(snapshot.tasks, t => t.type, taskTypes)
  const taskStates = distribution(snapshot.tasks, t => t.status, { created: '待分配', assigned: '已分配', executing: '执行中', completed: '已完成', cancelled: '已取消', failed: '失败' })
  const stations = distribution(snapshot.stations, s => s.type, stationTypes)
  const openEvents = snapshot.events.filter(e => e.status === 'open')
  const severity = distribution(openEvents, e => e.severity, { high: '高等级', medium: '中等级', low: '低等级' })
    .map(item => ({ ...item, color: item.key === 'high' ? '#ff708e' : item.key === 'medium' ? '#ffc45b' : '#37d9ff' }))
  const battery = snapshot.aircraft.map(a => ({
    key: a.id, label: a.id, value: Number.isFinite(a.battery) ? Math.min(100, Math.max(0, a.battery)) : null,
    color: a.battery <= 30 ? '#ffc45b' : '#35e6b2', name: a.name,
  }))
  const validBattery = battery.flatMap(item => item.value === null ? [] : [item.value])
  const averageBattery = validBattery.length ? validBattery.reduce((sum, n) => sum + n, 0) / validBattery.length : null
  // Never infer a completion timestamp from creation time or fabricate a historical trend.
  return {
    fleet, fleetTypes, taskKinds, taskStates, stations, severity, battery, averageBattery,
    enabledStations: snapshot.stations.filter(s => s.status === 'enabled').length,
    latestEvents: [...openEvents].sort((a, b) => b.id - a.id).slice(0, 3),
    latestTasks: snapshot.tasks.slice(0, 5), latestAudit: snapshot.audit.slice(0, 4),
  }
}

export function ringSegments(items: ChartDatum[]) {
  const total = items.reduce((sum, item) => sum + Math.max(0, item.value), 0)
  let offset = 0
  return items.map(item => {
    const percent = total > 0 ? Math.max(0, item.value) / total * 100 : 0
    const segment = { ...item, percent, offset }
    offset += percent
    return segment
  })
}
