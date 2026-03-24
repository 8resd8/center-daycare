# 데이터베이스 보안 정책 및 절차

## 1. 개요

본 문서는 요양보호시스템의 데이터베이스 보안 정책과 절차를 정의합니다. 개인정보보호법 및 관련 법규를 준수하고, 민감정보의 안전한 관리를 목적으로 합니다.

## 2. 민감정보 분류

### 🔴 고위험 정보 (즉시 보안 조치 필요)
- **수급자명**: 개인 식별의 핵심 정보
- **생년월일**: 개인식별정보
- **인정번호**: 공공기관 식별번호
- **비밀번호**: 인증 정보 (현재 평문 저장 - 최고 위험)

### 🟡 중위험 정보
- **성별**: 결합 시 식별 가능
- **차량번호**: 물적 식별정보
- **작성자명**: 업무 관련 식별정보

## 3. 보안 대책

### 3.1 암호화 정책

#### 비밀번호
- **방식**: bcrypt 해시 암호화
- **솔트**: 각 비밀번호별 고유 솔트
- **복호화**: 불가능 (단방향 해시)

#### 개인정보
- **방식**: AES-256 대칭키 암호화
- **키 관리**: 환경변수 또는 키 관리 시스템
- **복호화**: 권한 있는 사용자만 가능

### 3.2 접근 제어

#### 역할별 권한
```
ADMIN: 전체 정보 접근 + 감사 권한
MANAGER: 마스킹 정보 + 승인 권한  
EMPLOYEE: 마스킹 정보만 접근
```

#### 데이터 마스킹 규칙
- **이름**: 김*별 (첫글자와 마지막글자 제외 마스킹)
- **생년월일**: 1990-**-** (연도만 표시)
- **인정번호**: 완전 마스킹

### 3.3 감사 및 로깅

#### 기록 항목
- 접근자 ID, 시간, IP 주소
- 접근 대상, 유형 (MASKED/FULL/EMERGENCY)
- 접근 사유, 처리 결과

#### 보관 기간
- **접근 로그**: 3년
- **긴급 접근 기록**: 5년

## 4. 긴급 상황 대처 절차

### 4.1 긴급 접근 프로세스

1. **요청**: 긴급 상황 발생 시 상위 관리자에게 요청
2. **인증**: 이중 인증 (비밀번호 + OTP)
3. **승인**: 최고 관리자의 사전 승인
4. **기록**: 상세한 사유와 범위 기록
5. **감사**: 사후 감사 및 보고

### 4.2 긴급 접근 사유
- **의료 응급**: 환자 안전과 직접 관련된 상황
- **법적 요구**: 수사, 법원 명령 등 공적 요구
- **시스템 장애**: 데이터 복구 및 시스템 복구

## 5. 기술적 구현 가이드

### 5.1 데이터베이스 스키마 변경

```sql
-- 암호화 컬럼 추가
ALTER TABLE customers 
ADD COLUMN encrypted_name VARBINARY(255),
ADD COLUMN encrypted_birth_date VARBINARY(255),
ADD COLUMN encrypted_recognition_no VARBINARY(255);

-- 비밀번호 해시 컬럼 추가
ALTER TABLE users 
ADD COLUMN password_hash VARCHAR(255);

-- 접근 로그 테이블
CREATE TABLE access_logs (
    log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    access_type ENUM('MASKED', 'FULL', 'EMERGENCY') NOT NULL,
    access_reason TEXT,
    access_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT
);
```

### 5.2 애플리케이션 구현

```python
class SecureDataAccess:
    def __init__(self, db_connection, current_user_id):
        self.db = db_connection
        self.current_user_id = current_user_id
        self.encryption_key = os.getenv('DB_ENCRYPTION_KEY')
    
    def get_customer_info(self, customer_id: int, access_reason: str = ""):
        """권한별 고객 정보 조회"""
        user_role = self._get_user_role(self.current_user_id)
        self._log_access_attempt(customer_id, access_reason)
        
        if user_role == 'ADMIN':
            return self._get_full_info(customer_id)
        else:
            return self._get_masked_info(customer_id)
```

## 6. 정기적 보안 활동

### 6.1 월간 점검 항목
- [ ] 접근 로그 검토 및 이상 패턴 분석
- [ ] 암호화 키 유효성 확인
- [ ] 사용자 권한 정기적 검토
- [ ] 백업 데이터 암호화 상태 확인

### 6.2 분기별 보안 감사
- [ ] 전체 보안 정책 준수 여부 점검
- [ ] 취약점 스캔 및 평가
- [ ] 직원 보안 교육 실시
- [ ] 보안 정책 개선 검토

## 7. 위반 시 조치

### 7.1 보안 사고 처리 절차

1. **즉시 차단**: 관련 계정 및 접속 차단
2. **피해 분석**: 영향 범위 및 심각도 평가
3. **상급 보고**: 관리자 및 법무팀에 보고
4. **재발 방지**: 근본 원인 분석 및 대책 수립
5. **법적 조치**: 필요시 관련 당국 신고

### 7.2 징계 기준
- **1차 위반**: 경고 및 재교육
- **2차 위반**: 접근 권한 일시 정지
- **3차 위반**: 접근 권한 영구 정지 및 징계

## 8. 책임과 권한

### 8.1 역할별 책임
- **시스템 관리자**: 기술적 보안 구현 및 유지
- **정보보호 담당자**: 정책 수립 및 감사
- **부서장**: 소속 직원 권한 관리
- **전체 직원**: 보안 정책 준수

### 8.2 보고 체계
```
직원 → 부서장 → 정보보호 담당자 → 최고 경영자
```

## 9. 개인정보 보호법 준수

### 9.1 필수 항목
- 개인정보 수집·이용 동의
- 개인정보 처리 목적 명시
- 보유·이용 기간 설정
- 파기 절차 및 방법

### 9.2 정보주체 권리
- 개인정보 열람 요구권
- 정정·삭제 요구권
- 처리 정지 요구권

## 10. 부록

### 10.1 용어 정의
- **암호화**: 데이터를 비가독 형태로 변환
- **마스킹**: 데이터의 일부를 가려서 표시
- **접근 제어**: 권한에 따른 데이터 접근 통제

### 10.2 관련 법규
- 개인정보보호법
- 정보통신망법
- 의료법 (해당 시)

---

**문서 버전**: 1.0  
**작성일**: 2026-02-23  
**개정일**: 2026-02-23  
**승인자**: 정보보호 담당자
