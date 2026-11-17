-- Additive migration. UTC DATETIME(3); no existing business rows are changed.
CREATE TABLE IF NOT EXISTS st_position_device (
 id VARCHAR(64) PRIMARY KEY,
 name VARCHAR(80) NOT NULL,
 aircraft_id VARCHAR(40) NOT NULL UNIQUE,
 source VARCHAR(32) NOT NULL DEFAULT 'simulated_terminal',
 enabled TINYINT NOT NULL DEFAULT 0,
 session_id VARCHAR(64) NULL,
 last_sequence BIGINT NOT NULL DEFAULT -1,
 latest_sample_id BIGINT NULL,
 enabled_at DATETIME(3) NULL,
 created_by VARCHAR(64) NOT NULL,
 created_time DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
 CONSTRAINT fk_position_aircraft FOREIGN KEY (aircraft_id) REFERENCES st_aircraft(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS st_position_sample (
 id BIGINT PRIMARY KEY AUTO_INCREMENT,
 device_id VARCHAR(64) NOT NULL,
 session_id VARCHAR(64) NOT NULL,
 sequence_no BIGINT NOT NULL,
 sampled_at DATETIME(3) NOT NULL,
 received_at DATETIME(3) NOT NULL,
 longitude DOUBLE NOT NULL,
 latitude DOUBLE NOT NULL,
 altitude DOUBLE NOT NULL,
 fix_valid TINYINT NOT NULL,
 accepted TINYINT NOT NULL,
 verdict VARCHAR(40) NOT NULL,
 source VARCHAR(32) NOT NULL DEFAULT 'simulated_terminal',
 altitude_reference VARCHAR(40) NOT NULL DEFAULT 'relative_to_takeoff',
 UNIQUE KEY uk_position_sequence(device_id,session_id,sequence_no),
 KEY ix_position_track(device_id,sampled_at,id),
 CONSTRAINT fk_position_device FOREIGN KEY (device_id) REFERENCES st_position_device(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
