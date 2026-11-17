-- Additive, rerunnable. Plans store the exact algorithm/input/output for review.
SET NAMES utf8mb4;
CREATE TABLE IF NOT EXISTS st_dispatch_plan (
  id varchar(40) PRIMARY KEY,
  algorithm varchar(40) NOT NULL,
  status varchar(20) NOT NULL DEFAULT 'proposed',
  request_json json NOT NULL,
  result_json json NOT NULL,
  created_by varchar(64) NOT NULL,
  created_time datetime(3) NOT NULL,
  expires_at datetime(3) NOT NULL,
  confirmed_by varchar(64),
  confirmed_at datetime(3),
  reason varchar(500),
  INDEX idx_dispatch_created(created_time)
) ENGINE=InnoDB;
