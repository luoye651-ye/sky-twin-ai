-- Shared logical simulation clock + transactional launch serialization. No user rows rewritten.
CREATE TABLE IF NOT EXISTS st_traffic_clock (
 id INT PRIMARY KEY, tick BIGINT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
INSERT IGNORE INTO st_traffic_clock(id,tick) VALUES(1,0);
CREATE TABLE IF NOT EXISTS st_traffic_check (
 id VARCHAR(40) PRIMARY KEY, task_id VARCHAR(40) NOT NULL,
 allowed BOOLEAN NOT NULL, details_json JSON NOT NULL,
 created_by VARCHAR(64) NOT NULL,
 created_time DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
 KEY idx_traffic_check_task(task_id,created_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS st_traffic_plan (
 id VARCHAR(40) PRIMARY KEY,
 status VARCHAR(20) NOT NULL DEFAULT 'proposed',
 request_json JSON NOT NULL, result_json JSON NOT NULL,
 created_by VARCHAR(64) NOT NULL, confirmed_by VARCHAR(64), reason VARCHAR(500),
 created_time DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
 expires_at DATETIME(3) NOT NULL, confirmed_at DATETIME(3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS st_traffic_slot (
 task_id VARCHAR(40) PRIMARY KEY, plan_id VARCHAR(40) NOT NULL,
 route_revision INT NOT NULL, aircraft_id VARCHAR(40) NOT NULL,
 departure_tick BIGINT NOT NULL, duration_seconds INT NOT NULL,
 status VARCHAR(20) NOT NULL DEFAULT 'reserved',
 message VARCHAR(500) NOT NULL DEFAULT '',
 updated_time DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
 KEY idx_traffic_slot_due(status,departure_tick),
 CONSTRAINT fk_traffic_slot_task FOREIGN KEY(task_id) REFERENCES st_task(id) ON DELETE CASCADE,
 CONSTRAINT fk_traffic_slot_plan FOREIGN KEY(plan_id) REFERENCES st_traffic_plan(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
