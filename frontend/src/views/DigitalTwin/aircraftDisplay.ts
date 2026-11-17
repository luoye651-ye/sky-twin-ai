export const LOW_ALTITUDE_VISUAL_BASE = 220
export const LOW_ALTITUDE_VISUAL_STEP = 40
export const LOW_ALTITUDE_VISUAL_THRESHOLD = 120

export interface AircraftDisplayAltitude {
  displayAltitude: number
  reportedAltitude: number
  visualized: boolean
}

/**
 * Keep the business altitude untouched while lifting grounded/very-low aircraft
 * enough to remain legible above a kilometre-scale city model.
 */
export function resolveAircraftDisplayAltitude(reportedAltitude: number, visualSlot: number): AircraftDisplayAltitude {
  const safeAltitude = Number.isFinite(reportedAltitude) ? Math.max(0, reportedAltitude) : 0
  if (safeAltitude >= LOW_ALTITUDE_VISUAL_THRESHOLD) {
    return { displayAltitude: safeAltitude, reportedAltitude: safeAltitude, visualized: false }
  }
  return {
    displayAltitude: LOW_ALTITUDE_VISUAL_BASE + Math.max(0, visualSlot) % 4 * LOW_ALTITUDE_VISUAL_STEP,
    reportedAltitude: safeAltitude,
    visualized: true,
  }
}
