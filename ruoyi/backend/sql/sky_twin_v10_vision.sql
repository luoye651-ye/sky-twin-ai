-- User-upload inference evidence; no task state is owned by the calculator.
CREATE TABLE IF NOT EXISTS st_env_analysis (
 id VARCHAR(36) PRIMARY KEY, request_id VARCHAR(36) NOT NULL UNIQUE,
 status VARCHAR(16) NOT NULL, created_by VARCHAR(64) NOT NULL,
 created_time DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3), ended_time DATETIME(3),
 image_bytes MEDIUMBLOB NOT NULL, image_mime VARCHAR(20) NOT NULL,
 image_sha256 CHAR(64) NOT NULL, image_width INT NOT NULL, image_height INT NOT NULL,
 model_sha256 CHAR(64) NOT NULL, model_name VARCHAR(100) NOT NULL,
 result_json JSON, error_message VARCHAR(300), discovery_id VARCHAR(40) UNIQUE,
 KEY idx_env_analysis_status(status),
 CONSTRAINT fk_analysis_discovery FOREIGN KEY(discovery_id) REFERENCES st_env_discovery(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
