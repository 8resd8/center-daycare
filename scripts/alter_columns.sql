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

-- 직원 평가: record_id NULL 허용 (대시보드에서 직접 추가 시 일일기록 없음)
ALTER TABLE employee_evaluations
  MODIFY COLUMN record_id INT NULL;

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

-- 직원 피드백 리포트 (AI 생성, 월별 upsert)
CREATE TABLE IF NOT EXISTS employee_feedback_reports (
  report_id    BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT NOT NULL,
  target_month VARCHAR(7) NOT NULL,
  admin_note   TEXT,
  ai_result    JSON NOT NULL,
  created_at   DATETIME DEFAULT NOW(),
  updated_at   DATETIME DEFAULT NOW() ON UPDATE NOW(),
  UNIQUE KEY uq_user_month (user_id, target_month),
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
