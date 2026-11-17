export interface Location {
  lat: number
  lng: number
  alt: number
}

export type DroneStatus = 'idle' | 'flying' | 'returning'

export interface Drone {
  id: string
  name: string
  location: Location
  status: DroneStatus
}

export interface Mission {
  mission_id: string
  drone_id: string
  route: Location[]
  status: string
}
