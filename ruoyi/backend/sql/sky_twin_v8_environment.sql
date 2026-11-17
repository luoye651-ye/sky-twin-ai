-- Additive evidence workflow. Java remains the only task/business state authority.
CREATE TABLE IF NOT EXISTS st_env_discovery (
 id VARCHAR(40) PRIMARY KEY,
 request_id VARCHAR(36) NOT NULL UNIQUE, request_hash CHAR(64) NOT NULL,
 task_id VARCHAR(40) NOT NULL, title VARCHAR(80) NOT NULL,
 longitude DOUBLE NOT NULL, latitude DOUBLE NOT NULL, observed_at DATETIME(3) NOT NULL,
 image_source VARCHAR(24) NOT NULL, analysis_source VARCHAR(32) NOT NULL DEFAULT 'manual_annotation',
 image_bytes MEDIUMBLOB NOT NULL, image_mime VARCHAR(20) NOT NULL, image_sha256 CHAR(64) NOT NULL,
 image_width INT NOT NULL, image_height INT NOT NULL, original_name VARCHAR(100) NOT NULL,
 annotations_json JSON NOT NULL, status VARCHAR(24) NOT NULL DEFAULT 'pending_review',
 created_by VARCHAR(64) NOT NULL, created_time DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
 severity VARCHAR(10), event_id BIGINT UNIQUE, reviewed_by VARCHAR(64), reviewed_at DATETIME(3), review_reason VARCHAR(500),
 resolution VARCHAR(500), resolved_by VARCHAR(64), resolved_at DATETIME(3),
 after_bytes MEDIUMBLOB, after_mime VARCHAR(20), after_sha256 CHAR(64), after_width INT, after_height INT,
 KEY idx_env_discovery_status(status,created_time),
 CONSTRAINT fk_env_source_task FOREIGN KEY(task_id) REFERENCES st_task(id),
 CONSTRAINT fk_env_event FOREIGN KEY(event_id) REFERENCES st_event(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS st_env_response (
 id VARCHAR(40) PRIMARY KEY, discovery_id VARCHAR(40) NOT NULL,
 task_id VARCHAR(40) NOT NULL UNIQUE, attempt INT NOT NULL, priority INT NOT NULL,
 reason VARCHAR(500) NOT NULL, created_by VARCHAR(64) NOT NULL,
 created_time DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
 UNIQUE KEY uk_env_attempt(discovery_id,attempt),
 CONSTRAINT fk_env_response_discovery FOREIGN KEY(discovery_id) REFERENCES st_env_discovery(id),
 CONSTRAINT fk_env_response_task FOREIGN KEY(task_id) REFERENCES st_task(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS st_env_report (
 id VARCHAR(40) PRIMARY KEY, discovery_id VARCHAR(40) NOT NULL UNIQUE,
 content MEDIUMTEXT NOT NULL, snapshot_json JSON NOT NULL,
 created_by VARCHAR(64) NOT NULL, created_time DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
 CONSTRAINT fk_env_report_discovery FOREIGN KEY(discovery_id) REFERENCES st_env_discovery(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
