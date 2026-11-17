import type { TaskNavigation, Track } from '@sky/sky'
import type { AirspacePoint } from '@sky/airspace'

export interface FlightNavigationDisplay {
  taskId: string
  status: string
  points: AirspacePoint[]
  navigation: TaskNavigation
  tracks: Track[]
}
