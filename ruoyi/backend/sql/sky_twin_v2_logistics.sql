-- Additive: preserve existing orders and their task associations.
SET NAMES utf8mb4;
CREATE TABLE IF NOT EXISTS st_logistics_order (
  id varchar(40) PRIMARY KEY,
  cargo_name varchar(80) NOT NULL,
  weight decimal(10,2) NOT NULL,
  deadline_at datetime(3) NOT NULL,
  task_id varchar(40) NOT NULL UNIQUE,
  status varchar(20) NOT NULL DEFAULT 'created',
  created_by varchar(64) NOT NULL,
  created_time datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  delivered_by varchar(64),
  delivered_at datetime(3),
  FOREIGN KEY (task_id) REFERENCES st_task(id),
  INDEX idx_logistics_created (created_time)
) ENGINE=InnoDB;
