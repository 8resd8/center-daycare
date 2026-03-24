# React + FastAPI 마이그레이션 배포 가이드

> 인프라 담당자 전달용 문서
> 작성일: 2026-03-24

---

## 변경 사항 요약

| 항목 | 기존 (Streamlit) | 변경 후 (React + FastAPI) |
|------|-----------------|--------------------------|
| 백엔드 | Streamlit 단일 앱 (포트 8501) | FastAPI (포트 8000) |
| 프론트엔드 | Streamlit 내장 UI | React 18 + Nginx 컨테이너 (포트 3000) |
| Docker 이미지 | `arisa-internal-tool:latest` 1개 | `arisa-backend:latest` + `arisa-frontend:latest` 2개 |
| GitHub Actions | 완료 (코드에 반영됨) | — |
| docker-compose.prod.yml | 완료 (코드에 반영됨) | — |

GitHub Actions 워크플로우와 docker-compose.prod.yml은 이미 업데이트되어 있습니다.
**아래 항목만 서버에서 직접 작업이 필요합니다.**

---

## 1. 호스트 Nginx 설정 변경

기존에 Streamlit(:8501)으로 프록시하던 설정을 프론트엔드 컨테이너(:3000)로 변경합니다.

```nginx
# /etc/nginx/sites-available/arisa (또는 기존 설정 파일)

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## 2. GitHub Secrets — ENV_FILE 업데이트

GitHub 저장소 → Settings → Secrets and variables → Actions → `ENV_FILE` 시크릿 수정

기존 항목에 아래 두 줄을 **추가**하세요:

```env
GEMINI_API_KEY=...
OPENAI_API_KEY=...
```

---

## 3. MySQL 서비스 확인

기존에 외부(또는 별도) MySQL 서버를 사용 중이라면 `docker-compose.prod.yml`의 `mysql` 서비스를 제거하고 `.env`의 `DB_HOST`를 해당 DB 주소로 유지하면 됩니다.

현재 docker-compose로 MySQL을 함께 띄우고 있었다면 그대로 두면 됩니다.

---

## 4. 배포 검증 체크리스트

main 브랜치 머지 후 GitHub Actions 완료되면 아래 항목 확인:

- [ ] `docker ps` → `arisa-backend-prod`, `arisa-frontend-prod` 모두 Up
- [ ] `https://your-domain.com` → React 앱 로딩
- [ ] `https://your-domain.com/api/docs` → FastAPI Swagger UI 표시
- [ ] 수급자 목록 조회, 기록지 조회 정상 동작
- [ ] `docker logs arisa-backend-prod` — 에러 없음

---

## 5. 롤백 방법

```bash
cd /home/ec2-user/arisa

docker compose -f docker-compose.prod.yml down

# 이전 이미지 ID 확인
docker images | grep arisa

# 이전 이미지로 태그 복원 후 재시작
docker tag <이전_IMAGE_ID> arisa-backend:latest
docker tag <이전_IMAGE_ID> arisa-frontend:latest
docker compose -f docker-compose.prod.yml up -d
```
