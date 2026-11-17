SET NAMES utf8mb4;
CREATE TABLE IF NOT EXISTS st_airspace_policy (
 id int PRIMARY KEY, revision bigint NOT NULL DEFAULT 0
) ENGINE=InnoDB;
INSERT IGNORE INTO st_airspace_policy(id,revision) VALUES(1,0);
CREATE TABLE IF NOT EXISTS st_airspace_zone (
 id varchar(40) PRIMARY KEY, name varchar(80) NOT NULL, type varchar(20) NOT NULL,
 west double NOT NULL, south double NOT NULL, east double NOT NULL, north double NOT NULL,
 min_altitude double NOT NULL, max_altitude double NOT NULL,
 starts_at datetime(3), ends_at datetime(3), enabled tinyint NOT NULL,
 created_by varchar(64) NOT NULL, updated_by varchar(64) NOT NULL,
 created_time datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
 updated_time datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3), reason varchar(500) NOT NULL
) ENGINE=InnoDB;
-- Snapshot log deliberately has no task FK: REQUIRES_NEW denial records must not
-- wait on the task row held by the outer launch transaction that will roll back.
CREATE TABLE IF NOT EXISTS st_airspace_check (
 id varchar(40) PRIMARY KEY, task_id varchar(40) NOT NULL, task_title varchar(100) NOT NULL,
 entry varchar(30) NOT NULL, allowed tinyint NOT NULL, rule_revision bigint NOT NULL,
 departure_at datetime(3) NOT NULL, details_json json NOT NULL, created_by varchar(64) NOT NULL,
 created_time datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
 INDEX idx_airspace_check_created(created_time), INDEX idx_airspace_check_task(task_id,created_time)
) ENGINE=InnoDB;
