-- Additive operations extension. No existing task/resource/history is rewritten.
CREATE TABLE IF NOT EXISTS st_task_retry (
 request_id VARCHAR(36) PRIMARY KEY, source_task_id VARCHAR(40) NOT NULL, task_id VARCHAR(40) NOT NULL UNIQUE,
 created_by VARCHAR(64) NOT NULL, reason VARCHAR(500) NOT NULL, request_hash CHAR(64) NOT NULL, created_time DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
 FOREIGN KEY(source_task_id) REFERENCES st_task(id), FOREIGN KEY(task_id) REFERENCES st_task(id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS st_resource_operation (
 id VARCHAR(40) PRIMARY KEY, request_id VARCHAR(36) NOT NULL UNIQUE, aircraft_id VARCHAR(40) NOT NULL,
 kind VARCHAR(20) NOT NULL, status VARCHAR(16) NOT NULL DEFAULT 'active', reason VARCHAR(500) NOT NULL,
 initial_battery DOUBLE NOT NULL, final_battery DOUBLE, resolution VARCHAR(500), created_by VARCHAR(64) NOT NULL,
 created_time DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3), closed_by VARCHAR(64), closed_time DATETIME(3),
 FOREIGN KEY(aircraft_id) REFERENCES st_aircraft(id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS st_station_capacity (
 station_id VARCHAR(40) PRIMARY KEY, capacity INT NOT NULL, updated_by VARCHAR(64) NOT NULL,
 updated_time DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3), FOREIGN KEY(station_id) REFERENCES st_station(id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS st_commute_flight (
 id VARCHAR(40) PRIMARY KEY, request_id VARCHAR(36) NOT NULL UNIQUE, request_hash CHAR(64) NOT NULL, title VARCHAR(80) NOT NULL,
 start_station_id VARCHAR(40) NOT NULL, end_station_id VARCHAR(40) NOT NULL, departure_at DATETIME(3) NOT NULL,
 arrival_at DATETIME(3) NOT NULL, seats INT NOT NULL, revision INT NOT NULL DEFAULT 1,
 status VARCHAR(20) NOT NULL DEFAULT 'scheduled', task_id VARCHAR(40) UNIQUE,
 created_by VARCHAR(64) NOT NULL, created_time DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3), reason VARCHAR(500) NOT NULL,
 KEY idx_commute_schedule(status,departure_at,arrival_at), FOREIGN KEY(task_id) REFERENCES st_task(id), FOREIGN KEY(start_station_id) REFERENCES st_station(id), FOREIGN KEY(end_station_id) REFERENCES st_station(id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS st_commute_booking (
 id VARCHAR(40) PRIMARY KEY, request_id VARCHAR(36) NOT NULL UNIQUE, flight_id VARCHAR(40) NOT NULL,
 seats INT NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'confirmed', created_by VARCHAR(64) NOT NULL,
 created_time DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3), cancelled_time DATETIME(3),
 FOREIGN KEY(flight_id) REFERENCES st_commute_flight(id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS st_ops_report (
 id VARCHAR(40) PRIMARY KEY, request_id VARCHAR(36) NOT NULL UNIQUE, source_kind VARCHAR(20) NOT NULL,
 source_id VARCHAR(40) NOT NULL, title VARCHAR(150) NOT NULL, snapshot_json JSON NOT NULL, snapshot_sha256 CHAR(64) NOT NULL,
 created_by VARCHAR(64) NOT NULL, created_time DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
 revision INT NOT NULL DEFAULT 1, status VARCHAR(20) NOT NULL DEFAULT 'draft'
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS st_ops_report_version (
 report_id VARCHAR(40) NOT NULL, revision INT NOT NULL, content MEDIUMTEXT NOT NULL,
 source VARCHAR(20) NOT NULL, created_by VARCHAR(64) NOT NULL, created_time DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
 PRIMARY KEY(report_id,revision), FOREIGN KEY(report_id) REFERENCES st_ops_report(id)
) ENGINE=InnoDB;
