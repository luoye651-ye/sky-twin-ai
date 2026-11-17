import type { AirspaceCheck, AirspacePoint } from './airspace'
export interface RouteWaypoint { longitude: number; latitude: number }
export interface RoutePlan { revision: number; waypoints: RouteWaypoint[]; points: AirspacePoint[]; distanceMeters: number; durationSeconds: number; speed: number; cruiseAltitude: number }
export interface RouteDetail { taskId: string; title: string; status: string; plan: RoutePlan; versions: { revision: number; reason: string; createdBy: string; createdTime: string }[] }
export interface RouteInput { expectedRevision: number; waypoints: RouteWaypoint[]; reason: string }
export interface RouteEvaluation { plan: RoutePlan; check: AirspaceCheck; constraints: string[]; allowed: boolean; saved: boolean; serverTime: string }
export interface RouteSketch { points: Pick<AirspacePoint, 'longitude' | 'latitude' | 'altitude'>[]; waypoints: RouteWaypoint[]; altitude: number; selected: number }
