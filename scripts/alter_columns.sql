-- PII 암호화를 위한 컬럼 타입 변경 (Fernet base64 ~140자 → VARCHAR(500))
-- 실행 전 반드시 백업: mysqldump -u<user> -p <db> customers users > backup.sql

ALTER TABLE customers
  MODIFY COLUMN name          VARCHAR(500) NOT NULL,
  MODIFY COLUMN birth_date    VARCHAR(500) NULL,
  MODIFY COLUMN recognition_no VARCHAR(500) NULL,
  MODIFY COLUMN facility_name  VARCHAR(500) NULL,
  MODIFY COLUMN facility_code  VARCHAR(500) NULL;

ALTER TABLE users
  MODIFY COLUMN name          VARCHAR(500) NOT NULL,
  MODIFY COLUMN birth_date    VARCHAR(500) NULL;

-- 감사 로그 테이블
CREATE TABLE IF NOT EXISTS audit_logs (
  log_id     BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT    NOT NULL,
  action     ENUM('READ','CREATE','UPDATE','DELETE') NOT NULL,
  resource   VARCHAR(50) NOT NULL,
  res_id     BIGINT NULL,
  ip         VARCHAR(45) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_audit_user (user_id),
  INDEX idx_audit_resource (resource, res_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
