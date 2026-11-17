-- Immutable route revisions. No existing task or track is rewritten.
CREATE TABLE IF NOT EXISTS st_task_route (
 id VARCHAR(40) PRIMARY KEY,
 task_id VARCHAR(40) NOT NULL,
 revision INT NOT NULL,
 plan_json JSON NOT NULL,
 reason VARCHAR(500) NOT NULL,
 created_by VARCHAR(64) NOT NULL,
 created_time DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
 UNIQUE KEY uk_task_route_revision(task_id,revision),
 CONSTRAINT fk_route_task FOREIGN KEY(task_id) REFERENCES st_task(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS st_dispatch_route_snapshot (
 plan_id VARCHAR(40) NOT NULL,
 task_id VARCHAR(40) NOT NULL,
 route_revision INT NOT NULL,
 PRIMARY KEY(plan_id,task_id),
 CONSTRAINT fk_dispatch_route_plan FOREIGN KEY(plan_id) REFERENCES st_dispatch_plan(id) ON DELETE CASCADE,
 CONSTRAINT fk_dispatch_route_task FOREIGN KEY(task_id) REFERENCES st_task(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
