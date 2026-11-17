import type { NmeaFrame } from '../../../shared/positioning.ts'

/** Synthetic GB/GGA payload, not a satellite observation or browser geolocation. */
export function makeBeidouDemoFrame(point: {longitude:number;latitude:number;altitude:number}, sampledAt: string, fixValid=true, takeoffAltitudeMsl=12): NmeaFrame {
  const date=new Date(sampledAt)
  if (!Number.isFinite(date.getTime()) || ![point.longitude,point.latitude,point.altitude,takeoffAltitudeMsl].every(Number.isFinite)
      || Math.abs(point.longitude)>180 || Math.abs(point.latitude)>90) throw new Error('北斗演示样例的时间或坐标无效')
  function degreesMinutes(value:number, digits:number) {
    // Round total minutes before splitting to avoid illegal 59.999999 -> 60.00000 minutes.
    const totalMinutes=Math.round(Math.abs(value)*60*1e5)/1e5
    const degrees=Math.floor(totalMinutes/60), minutes=totalMinutes-degrees*60
    return String(degrees).padStart(digits,'0')+minutes.toFixed(5).padStart(8,'0')
  }
  const utc=date.toISOString(), time=utc.slice(11,23).replace(/:/g,'')
  const body=['GBGGA',time,degreesMinutes(point.latitude,2),point.latitude<0?'S':'N',degreesMinutes(point.longitude,3),point.longitude<0?'W':'E',
    fixValid?'1':'0',fixValid?'12':'00',fixValid?'0.9':'99.9',(takeoffAltitudeMsl+point.altitude).toFixed(2),'M','0.0','M','',''].join(',')
  let checksum=0
  for(const char of body) checksum^=char.charCodeAt(0)
  return {gga:`$${body}*${checksum.toString(16).toUpperCase().padStart(2,'0')}`,utcDate:utc.slice(0,10),takeoffAltitudeMsl}
}
