# 서버 운영 매뉴얼 (React + FastAPI)

> 브랜치: `feat/react-fastapi-migration`
> 최종 수정: 2026-03-24

---

## 1. 로컬 개발 서버

### 1-1. 실행 방법

터미널을 **두 개** 열고 각각 실행한다.

**터미널 A — Backend**
```bash
cd C:\git-project\arisa_internal_tool
uvicorn backend.main:app --reload --port 8000
```

**터미널 B — Frontend**
```bash
cd C:\git-project\arisa_internal_tool\frontend
npm run dev
```

| 서비스 | URL |
|--------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API 문서 (Swagger) | http://localhost:8000/docs |

---

### 1-2. 종료 방법

각 터미널에서 `Ctrl+C`

백그라운드에서 실행 중인 경우:
```bash
# 포트 8000 사용 중인 프로세스 종료 (backend)
netstat -ano | findstr :8000
taskkill /PID <PID번호> /F

# 포트 5173 사용 중인 프로세스 종료 (frontend)
netstat -ano | findstr :5173
taskkill /PID <PID번호> /F
```

---

### 1-3. 필수 환경 변수 (`.env`)

프로젝트 루트에 `.env` 파일 필요. 없으면 복사해서 값 채우기.

```env
# MySQL
DB_HOST=localhost
DB_PORT=3306
DB_NAME=center_care
DB_USER=resd
DB_PASSWORD=<비밀번호>

# AI
GEMINI_API_KEY=<Gemini API 키>
OPENAI_API_KEY=<OpenAI API 키>

# 기타
PYTHONUNBUFFERED=1
```

> `.streamlit/secrets.toml`도 DB 연결 fallback으로 사용됨
> 우선순위: **env vars > secrets.toml**

---

### 1-4. 패키지 재설치 필요할 때

```bash
# Backend
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install
```

---

## 2. EC2 서버 배포 절차

> EC2 OS: Ubuntu / arisa.pro 도메인 연결 가정

---

### 2-1. 최초 1회 — 서버 초기 세팅

```bash
# Docker, Docker Compose 설치
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker

# 프로젝트 클론
git clone https://github.com/8resd8/daycare-record.git
cd daycare-record
git checkout feat/react-fastapi-migration
```

---

### 2-2. `.env` 파일 EC2에 생성

```bash
vi .env
```

```env
DB_HOST=mysql          # docker-compose 네트워크 내부 서비스명
DB_PORT=3306
DB_NAME=center_care
DB_USER=root           # 또는 별도 유저
DB_PASSWORD=<비밀번호>
GEMINI_API_KEY=<키>
OPENAI_API_KEY=<키>
PYTHONUNBUFFERED=1
```

---

### 2-3. Docker 이미지 빌드

```bash
# Backend 이미지 빌드 (루트 디렉토리에서)
docker build -f backend/Dockerfile -t arisa-backend:latest .

# Frontend 이미지 빌드
docker build -f frontend/Dockerfile -t arisa-frontend:latest ./frontend
```

---

### 2-4. 프로덕션 실행

```bash
docker compose -f docker-compose.prod.yml up -d
```

실행 확인:
```bash
docker ps
# arisa-backend-prod, arisa-frontend-prod, mysql 세 컨테이너 running 확인
```

---

### 2-5. 배포 업데이트 (코드 변경 시)

```bash
# 1. 최신 코드 받기
git pull origin feat/react-fastapi-migration

# 2. 이미지 재빌드
docker build -f backend/Dockerfile -t arisa-backend:latest .
docker build -f frontend/Dockerfile -t arisa-frontend:latest ./frontend

# 3. 컨테이너 재시작
docker compose -f docker-compose.prod.yml up -d --no-deps backend frontend
```

> `--no-deps` 옵션으로 mysql 재시작 없이 앱만 교체 가능

---

### 2-6. 로그 확인

```bash
# 실시간 로그
docker logs -f arisa-backend-prod
docker logs -f arisa-frontend-prod

# 최근 100줄
docker logs --tail=100 arisa-backend-prod
```

---

### 2-7. 서비스 중지 / 재시작

```bash
# 전체 중지 (DB 유지)
docker compose -f docker-compose.prod.yml stop

# 전체 재시작
docker compose -f docker-compose.prod.yml restart

# 특정 서비스만 재시작
docker compose -f docker-compose.prod.yml restart backend
```

---

### 2-8. Nginx HTTPS 설정 (SSL, Let's Encrypt)

```bash
# certbot 설치
sudo apt install certbot

# 인증서 발급 (80포트 일시 중지 필요)
docker compose -f docker-compose.prod.yml stop frontend
sudo certbot certonly --standalone -d arisa.pro -d www.arisa.pro

# 인증서 경로 확인
ls /etc/letsencrypt/live/arisa.pro/
# fullchain.pem, privkey.pem
```

`frontend/nginx.conf`에 SSL 블록 추가 후 이미지 재빌드:
```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/arisa.pro/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/arisa.pro/privkey.pem;
    ...
}
```

`docker-compose.prod.yml` frontend 볼륨에 인증서 마운트:
```yaml
volumes:
  - /etc/letsencrypt:/etc/letsencrypt:ro
```

---

### 2-9. DB 백업 (MySQL)

```bash
# 덤프
docker exec mysql mysqldump -u root -p center_care > backup_$(date +%Y%m%d).sql

# 복원
docker exec -i mysql mysql -u root -p center_care < backup_20260324.sql
```

---

## 3. 트러블슈팅

| 증상 | 확인 사항 |
|------|-----------|
| `DB 연결 실패` | `.env`의 `DB_HOST`, `DB_PASSWORD` 확인. 로컬이면 `localhost`, Docker면 `mysql` |
| `502 Bad Gateway` | backend 컨테이너 상태 확인 (`docker ps`), 로그 확인 |
| `AI 평가 실패` | `GEMINI_API_KEY` / `OPENAI_API_KEY` 환경변수 확인 |
| `포트 충돌` | `netstat -ano \| findstr :8000` 으로 PID 확인 후 종료 |
| `npm run build 실패` | `node --version` 확인 (v18 이상 필요), `npm install` 재실행 |

---

## 4. 디렉토리 구조 요약

```
arisa_internal_tool/
├── backend/           ← FastAPI (uvicorn)
│   ├── main.py
│   ├── routers/       ← 8개 라우터
│   ├── schemas/       ← Pydantic 모델
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/          ← React + Vite
│   ├── src/
│   │   ├── pages/     ← 4개 페이지
│   │   ├── api/       ← axios 함수
│   │   ├── store/     ← Zustand
│   │   └── types/
│   ├── Dockerfile
│   └── nginx.conf
├── modules/           ← 기존 Python 로직 (변경 없음)
│   ├── repositories/
│   ├── services/
│   └── clients/
├── docker-compose.yml          ← 개발용
├── docker-compose.prod.yml     ← 프로덕션
└── .env                        ← 환경변수 (git 제외)
```
