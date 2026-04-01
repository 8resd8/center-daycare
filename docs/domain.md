# 도메인 모델 및 DB 스키마

## 도메인 용어

| 한국어 | 코드명 | 설명 |
|--------|--------|------|
| 수급자 | Customer | 주간보호센터 이용자 |
| 직원 | Employee / User | 시설 직원 (시스템 사용자) |
| 기록지 | Daily Record | 일일 서비스 기록 (daily_infos + 4개 서브 테이블) |
| 주간 보고서 | Weekly Report | 주간 상태변화 AI 생성 보고서 |
| AI 평가 | AI Evaluation | 기록지 특이사항 자동 평가 |
| 직원 평가 | Employee Evaluation | 직원 기록 오류/누락 수동 지적 |
| 지적 | Evaluation Point | 직원 평가 1건 |

### 직원 평가 카테고리 / 유형

- **카테고리**: `공통` / `신체` / `인지` / `간호` / `기능`
- **유형**: `누락` / `내용부족` / `오타` / `문법` / `오류`

### AI 평가 등급

| 등급 | 코드 | 점수 |
|------|------|------|
| 우수 | excellent | 3 |
| 평균 | average | 2 |
| 개선 | improvement | 1 |

---

## DB 테이블 구조

### customers
```sql
customer_id     INT AUTO_INCREMENT PRIMARY KEY
name            VARCHAR(500) NOT NULL       -- Fernet 암호화
birth_date      VARCHAR(500) NULL           -- Fernet 암호화
gender          VARCHAR(10) NULL
recognition_no  VARCHAR(500) NULL           -- Fernet 암호화
benefit_start_date DATE NULL
grade           VARCHAR(20) NULL
facility_name   VARCHAR(500) NULL           -- Fernet 암호화
facility_code   VARCHAR(500) NULL           -- Fernet 암호화
created_at      DATETIME
updated_at      DATETIME
```

### users
```sql
user_id         INT AUTO_INCREMENT PRIMARY KEY
username        VARCHAR(50) NOT NULL UNIQUE
password        VARCHAR(255) NOT NULL       -- bcrypt (rounds=12)
role            ENUM('ADMIN','EMPLOYEE') DEFAULT 'EMPLOYEE'
name            VARCHAR(500) NOT NULL       -- Fernet 암호화
gender          VARCHAR(10) NULL
birth_date      VARCHAR(500) NULL           -- Fernet 암호화
work_status     VARCHAR(20) DEFAULT '재직'  -- '재직' | '퇴사'
job_type        VARCHAR(100) NULL
hire_date       VARCHAR(50) NULL
resignation_date DATE NULL
license_name    VARCHAR(100) NULL
license_date    DATE NULL
```

### daily_infos
```sql
record_id       INT AUTO_INCREMENT PRIMARY KEY
customer_id     INT NOT NULL FK→customers
date            DATE NOT NULL
start_time      VARCHAR(20) NULL
end_time        VARCHAR(20) NULL
total_service_time VARCHAR(100) NULL
transport_service  VARCHAR(50) NULL
transport_vehicles VARCHAR(50) NULL
UNIQUE (customer_id, date)
```

### daily_physicals
```sql
physical_id     INT AUTO_INCREMENT PRIMARY KEY
record_id       INT NOT NULL FK→daily_infos
hygiene_care    VARCHAR(100) NULL
bath_time       VARCHAR(100) NULL
bath_method     VARCHAR(100) NULL
meal_breakfast  VARCHAR(50) NULL
meal_lunch      VARCHAR(50) NULL
meal_dinner     VARCHAR(50) NULL
toilet_care     VARCHAR(100) NULL
mobility_care   VARCHAR(100) NULL
note            TEXT NULL
writer_name     VARCHAR(100) NULL
```

### daily_cognitives
```sql
cognitive_id    INT AUTO_INCREMENT PRIMARY KEY
record_id       INT NOT NULL FK→daily_infos
cog_support     VARCHAR(100) NULL
comm_support    VARCHAR(100) NULL
note            TEXT NULL
writer_name     VARCHAR(100) NULL
```

### daily_nursings
```sql
nursing_id      INT AUTO_INCREMENT PRIMARY KEY
record_id       INT NOT NULL FK→daily_infos
bp_temp         VARCHAR(100) NULL
health_manage   VARCHAR(100) NULL
nursing_manage  VARCHAR(100) NULL
emergency       VARCHAR(100) NULL
note            TEXT NULL
writer_name     VARCHAR(100) NULL
```

### daily_recoveries
```sql
recovery_id     INT AUTO_INCREMENT PRIMARY KEY
record_id       INT NOT NULL FK→daily_infos
prog_basic      VARCHAR(50) NULL
prog_activity   VARCHAR(50) NULL
prog_cognitive  VARCHAR(50) NULL
prog_therapy    VARCHAR(100) NULL
prog_enhance_detail TEXT NULL
note            TEXT NULL
writer_name     VARCHAR(100) NULL
```

### ai_evaluations
```sql
ai_eval_id      INT AUTO_INCREMENT PRIMARY KEY
record_id       INT NOT NULL FK→daily_infos
category        VARCHAR(20) NOT NULL        -- '신체'|'인지'|'간호'|'기능'
oer_fidelity    VARCHAR(10) NULL            -- 'O'|'X'
specificity_score VARCHAR(10) NULL          -- 'O'|'X'
grammar_score   VARCHAR(10) NULL            -- 'O'|'X'
grade_code      VARCHAR(20) NULL            -- '우수'|'평균'|'개선'
reason_text     TEXT NULL
suggestion_text TEXT NULL
original_text   TEXT NULL
UNIQUE (record_id, category)
```

### weekly_status
```sql
status_id       INT AUTO_INCREMENT PRIMARY KEY
customer_id     INT NOT NULL FK→customers
start_date      DATE NOT NULL
end_date        DATE NOT NULL
report_text     LONGTEXT
UNIQUE (customer_id, start_date, end_date)
```

### employee_evaluations
```sql
emp_eval_id         INT AUTO_INCREMENT PRIMARY KEY
record_id           INT NULL FK→daily_infos   -- 직접 추가 시 NULL 가능
target_date         DATE NULL
target_user_id      INT NOT NULL FK→users
evaluator_user_id   INT NULL FK→users
category            VARCHAR(20) NOT NULL      -- '공통'|'신체'|'인지'|'간호'|'기능'
evaluation_type     VARCHAR(20) NOT NULL      -- '누락'|'내용부족'|'오타'|'문법'|'오류'
score               INT DEFAULT 1
comment             TEXT NULL
evaluation_date     DATE NOT NULL
INDEX (target_user_id, evaluation_date)
```

### audit_logs
```sql
log_id      BIGINT AUTO_INCREMENT PRIMARY KEY
user_id     INT NOT NULL
action      ENUM('READ','CREATE','UPDATE','DELETE') NOT NULL
resource    VARCHAR(50) NOT NULL
res_id      BIGINT NULL
ip          VARCHAR(45) NULL
created_at  DATETIME
```

---

## 관계 다이어그램

```
customers
  └── daily_infos (1:N, customer_id)
        ├── daily_physicals (1:1, record_id)
        ├── daily_cognitives (1:1, record_id)
        ├── daily_nursings (1:1, record_id)
        ├── daily_recoveries (1:1, record_id)
        ├── ai_evaluations (1:N, record_id, UNIQUE per category)
        └── employee_evaluations (1:N, record_id)
  └── weekly_status (1:N, customer_id, UNIQUE per period)

users
  └── employee_evaluations (target_user_id, evaluator_user_id)
  └── audit_logs (user_id)
```
