-- Evaluation records only. No aircraft/task/event state changes.
CREATE TABLE IF NOT EXISTS st_patrol_eval_guard (id INT PRIMARY KEY) ENGINE=InnoDB;
INSERT IGNORE INTO st_patrol_eval_guard(id) VALUES(1);
CREATE TABLE IF NOT EXISTS st_patrol_eval (
 id CHAR(36) PRIMARY KEY, request_id CHAR(36) NOT NULL UNIQUE,
 status VARCHAR(16) NOT NULL, stage VARCHAR(24) NOT NULL, processed INT NOT NULL DEFAULT 0,
 model_name VARCHAR(120) NOT NULL, model_sha256 CHAR(64) NOT NULL, dataset_sha256 CHAR(64) NOT NULL,
 image_count INT NOT NULL DEFAULT 132, created_by VARCHAR(64) NOT NULL,
 created_time DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3), started_time DATETIME(3), ended_time DATETIME(3),
 error_message VARCHAR(500), report_json MEDIUMTEXT, report_sha256 CHAR(64),
 KEY idx_patrol_state(status,created_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS st_patrol_eval_request (
 request_id CHAR(36) PRIMARY KEY, run_id CHAR(36) NOT NULL, actor VARCHAR(64) NOT NULL,
 created_time DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
 KEY idx_patrol_request_run(run_id),
 CONSTRAINT fk_patrol_request_run FOREIGN KEY(run_id) REFERENCES st_patrol_eval(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
INSERT IGNORE INTO st_patrol_eval_request(request_id,run_id,actor)
 SELECT request_id,id,created_by FROM st_patrol_eval;
