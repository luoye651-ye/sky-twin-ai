-- Move only untouched legacy Shanghai demo coordinates into the Hangzhou urban-core simulation.
-- IDs and foreign-key relationships stay unchanged; rerunning is safe because migrated rows no longer match.
SET NAMES utf8mb4;
START TRANSACTION;

INSERT INTO st_audit(entity_id, action, reason, actor)
SELECT id, 'station.coordinate.migrate', '旧上海演示坐标迁移为杭州主城区仿真站点；保留站点编号和业务关联', 'system-migration'
FROM st_station
WHERE id IN ('S-01','S-02','S-03','S-04','S-05','S-06')
  AND longitude BETWEEN 121.46 AND 121.49 AND latitude BETWEEN 31.22 AND 31.24;

UPDATE st_station
SET longitude = CASE id
      WHEN 'S-01' THEN 120.1900 WHEN 'S-02' THEN 120.3450 WHEN 'S-03' THEN 120.0800
      WHEN 'S-04' THEN 120.1600 WHEN 'S-05' THEN 120.2050 WHEN 'S-06' THEN 120.4340 END,
    latitude = CASE id
      WHEN 'S-01' THEN 30.1950 WHEN 'S-02' THEN 30.2920 WHEN 'S-03' THEN 30.2700
      WHEN 'S-04' THEN 30.2600 WHEN 'S-05' THEN 30.1750 WHEN 'S-06' THEN 30.2360 END
WHERE id IN ('S-01','S-02','S-03','S-04','S-05','S-06')
  AND longitude BETWEEN 121.46 AND 121.49 AND latitude BETWEEN 31.22 AND 31.24;

INSERT INTO st_audit(entity_id, action, reason, actor)
SELECT id, 'aircraft.coordinate.migrate', '空闲飞行器随旧上海演示停放点迁移到对应杭州仿真站点', 'system-migration'
FROM st_aircraft
WHERE status = 'idle' AND longitude BETWEEN 121.46 AND 121.49 AND latitude BETWEEN 31.22 AND 31.24;

UPDATE st_aircraft AS aircraft
JOIN (
  SELECT 121.4737 old_lon, 31.2304 old_lat, 120.1900 new_lon, 30.1950 new_lat UNION ALL
  SELECT 121.4807, 31.2334, 120.3450, 30.2920 UNION ALL
  SELECT 121.4697, 31.2334, 120.0800, 30.2700 UNION ALL
  SELECT 121.4767, 31.2264, 120.1600, 30.2600 UNION ALL
  SELECT 121.4717, 31.2284, 120.2050, 30.1750 UNION ALL
  SELECT 121.4807, 31.2284, 120.4340, 30.2360
) AS mapping
  ON ABS(aircraft.longitude - mapping.old_lon) < 0.000001
 AND ABS(aircraft.latitude - mapping.old_lat) < 0.000001
SET aircraft.longitude = mapping.new_lon, aircraft.latitude = mapping.new_lat
WHERE aircraft.status = 'idle';

COMMIT;
