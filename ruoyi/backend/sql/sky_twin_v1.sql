-- Additive migration: only SkyTwin tables; never drop existing RuoYi data.
SET NAMES utf8mb4;
CREATE TABLE IF NOT EXISTS st_aircraft (
 id varchar(40) PRIMARY KEY, name varchar(80) NOT NULL, type varchar(20) NOT NULL,
 model varchar(80) NOT NULL, longitude double NOT NULL, latitude double NOT NULL,
 altitude double NOT NULL DEFAULT 0, battery double NOT NULL DEFAULT 100,
 payload_capacity double NOT NULL DEFAULT 0, seats int NOT NULL DEFAULT 0,
 status varchar(20) NOT NULL DEFAULT 'idle', speed double NOT NULL DEFAULT 0,
 deleted tinyint NOT NULL DEFAULT 0, created_time datetime(3) DEFAULT CURRENT_TIMESTAMP(3)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS st_station (
 id varchar(40) PRIMARY KEY, name varchar(80) NOT NULL, type varchar(20) NOT NULL,
 longitude double NOT NULL, latitude double NOT NULL,
 status varchar(20) NOT NULL DEFAULT 'enabled', deleted tinyint NOT NULL DEFAULT 0,
 created_time datetime(3) DEFAULT CURRENT_TIMESTAMP(3)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS st_task (
 id varchar(40) PRIMARY KEY, title varchar(100) NOT NULL, type varchar(20) NOT NULL,
 aircraft_id varchar(40), start_station_id varchar(40) NOT NULL, end_station_id varchar(40) NOT NULL,
 payload double NOT NULL DEFAULT 0, passengers int NOT NULL DEFAULT 0,
 status varchar(20) NOT NULL DEFAULT 'created', progress double NOT NULL DEFAULT 0,
 speed double NOT NULL, cruise_altitude double NOT NULL, duration_seconds int NOT NULL DEFAULT 60,
 elapsed_seconds int NOT NULL DEFAULT 0, reason varchar(500) NOT NULL,
 created_by varchar(64) NOT NULL, created_time datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
 updated_time datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
 FOREIGN KEY (aircraft_id) REFERENCES st_aircraft(id),
 FOREIGN KEY (start_station_id) REFERENCES st_station(id),
 FOREIGN KEY (end_station_id) REFERENCES st_station(id), INDEX idx_task_status(status)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS st_track (
 id bigint PRIMARY KEY AUTO_INCREMENT, task_id varchar(40) NOT NULL, aircraft_id varchar(40) NOT NULL,
 longitude double NOT NULL, latitude double NOT NULL, altitude double NOT NULL,
 battery double NOT NULL, speed double NOT NULL, progress double NOT NULL,
 recorded_time datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
 FOREIGN KEY (task_id) REFERENCES st_task(id), INDEX idx_track_task(task_id, id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS st_event (
 id bigint PRIMARY KEY AUTO_INCREMENT, task_id varchar(40), aircraft_id varchar(40),
 severity varchar(20) NOT NULL, title varchar(200) NOT NULL,
 status varchar(20) NOT NULL DEFAULT 'open', resolution varchar(500), resolved_by varchar(64),
 created_time datetime(3) DEFAULT CURRENT_TIMESTAMP(3), resolved_time datetime(3),
 FOREIGN KEY (task_id) REFERENCES st_task(id), INDEX idx_event_status(status)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS st_report (
 id bigint PRIMARY KEY AUTO_INCREMENT, task_id varchar(40) NOT NULL UNIQUE,
 title varchar(150) NOT NULL, content text NOT NULL, created_by varchar(64) NOT NULL,
 created_time datetime(3) DEFAULT CURRENT_TIMESTAMP(3), FOREIGN KEY (task_id) REFERENCES st_task(id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS st_audit (
 id bigint PRIMARY KEY AUTO_INCREMENT, entity_id varchar(40) NOT NULL, action varchar(40) NOT NULL,
 reason varchar(500) NOT NULL, actor varchar(64) NOT NULL,
 created_time datetime(3) DEFAULT CURRENT_TIMESTAMP(3), INDEX idx_audit_entity(entity_id, id)
) ENGINE=InnoDB;

INSERT IGNORE INTO st_station(id,name,type,longitude,latitude) VALUES
 ('S-01','滨江起降点','takeoff',120.1900,30.1950),
 ('S-02','东岸物流站','logistics',120.3450,30.2920),
 ('S-03','西岸充电点','charging',120.0800,30.2700),
 ('S-04','应急物资站','emergency',120.1600,30.2600),
 ('S-05','滨江 eVTOL 起降场','vertiport',120.2050,30.1750),
 ('S-06','东岸 eVTOL 起降场','vertiport',120.4340,30.2360);
INSERT IGNORE INTO st_aircraft(id,name,type,model,longitude,latitude,battery,payload_capacity,seats) VALUES
 ('D-01','巡检无人机 D-01','drone','Sim-Scout',120.1900,30.1950,100,2,0),
 ('D-02','巡检无人机 D-02','drone','Sim-Scout',120.0800,30.2700,90,2,0),
 ('C-01','货运无人机 C-01','cargo','Sim-Cargo',120.1900,30.1950,100,20,0),
 ('E-01','通勤 eVTOL E-01','evtol','Sim-eVTOL',120.2050,30.1750,100,100,4);

-- Use generated menu IDs and resolve by paths/permission keys: safe to rerun.
INSERT INTO sys_menu(menu_name,parent_id,order_num,path,menu_type,visible,status,icon,create_by,create_time)
 SELECT '低空业务',0,0,'sky-twin','M','0','0','dashboard','admin',NOW()
 WHERE NOT EXISTS(SELECT 1 FROM sys_menu WHERE parent_id=0 AND path='sky-twin');
SET @parent=(SELECT menu_id FROM sys_menu WHERE parent_id=0 AND path='sky-twin' LIMIT 1);
INSERT INTO sys_menu(menu_name,parent_id,order_num,path,component,menu_type,visible,status,perms,icon,create_by,create_time)
 SELECT label,@parent,seq,path,component,'C','0','0','sky:read','list','admin',NOW() FROM (
 SELECT '飞行器管理' label,1 seq,'aircraft' path,'sky-twin/aircraft/index' component UNION ALL
 SELECT '站点管理',2,'stations','sky-twin/stations/index' UNION ALL
 SELECT '统一任务管理',3,'tasks','sky-twin/tasks/index' UNION ALL
 SELECT '异常事件',4,'events','sky-twin/events/index' UNION ALL
 SELECT '任务报告',5,'reports','sky-twin/reports/index' UNION ALL
 SELECT '操作记录',6,'audit','sky-twin/audit/index') x
 WHERE NOT EXISTS(SELECT 1 FROM sys_menu m WHERE m.parent_id=@parent AND m.path=x.path);
INSERT INTO sys_menu(menu_name,parent_id,order_num,path,menu_type,visible,status,perms,create_by,create_time)
 SELECT label,@parent,seq,'','F','0','0',perm,'admin',NOW() FROM (
 SELECT '资源维护' label,20 seq,'sky:manage' perm UNION ALL SELECT '任务调度',21,'sky:operate') x
 WHERE NOT EXISTS(SELECT 1 FROM sys_menu m WHERE m.perms=x.perm);
INSERT INTO sys_role(role_name,role_key,role_sort,data_scope,status,del_flag,create_by,create_time,remark)
 SELECT '低空调度员','sky_dispatcher',3,'1','0','0','admin',NOW(),'创建、分配、执行任务及处置告警'
 WHERE NOT EXISTS(SELECT 1 FROM sys_role WHERE role_key='sky_dispatcher');
INSERT INTO sys_role(role_name,role_key,role_sort,data_scope,status,del_flag,create_by,create_time,remark)
 SELECT '低空查看者','sky_viewer',4,'1','0','0','admin',NOW(),'仅查看业务数据'
 WHERE NOT EXISTS(SELECT 1 FROM sys_role WHERE role_key='sky_viewer');
INSERT IGNORE INTO sys_role_menu(role_id,menu_id)
 SELECT r.role_id,m.menu_id FROM sys_role r JOIN sys_menu m ON (m.menu_id=@parent OR m.parent_id=@parent)
 WHERE r.role_key IN('sky_dispatcher','sky_viewer') AND (m.perms='sky:read' OR m.menu_id=@parent OR (r.role_key='sky_dispatcher' AND m.perms='sky:operate'));
