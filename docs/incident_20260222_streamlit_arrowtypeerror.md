# 장애 보고서: Streamlit 무한 로딩(ArrowTypeError) (2026-02-22)

## 1) 현상
- **서비스**: `mcplink.co.kr/boeun`
- **증상**: 웹 접속 시 무한 로딩(응답 지연/페이지 렌더링 멈춤)
- **임시 조치**: Docker 컨테이너 재시작 후 정상 접속

## 2) 당시 확인했어야 할 것(우선순위)

### 2-1. 컨테이너/애플리케이션 표준 로그
- **Streamlit 앱 로그**
  - `docker logs <container> --since "2026-02-22T05:50:00"`
  - 에러 키워드:
    - `Traceback`
    - `ArrowTypeError`
    - `Exception`
    - `Killed` / `OOM`

### 2-2. 리소스/프로세스 상태
- **CPU/메모리 급증 여부**
  - `docker stats <container>`
- **OOM(Kernel OOM Killer) 여부**
  - 호스트에서 `dmesg` 또는 시스템 로그 확인(권한 필요)

### 2-3. Reverse Proxy(Nginx 등) 사용 시
- **Nginx access/error 로그**
  - 502/504(Upstream timeout) 여부

## 3) 로그 해석(핵심)

### 3-1. DataFrame → Arrow 직렬화 실패
로그:
```
Serialization of dataframe to Arrow table was unsuccessful...
pyarrow.lib.ArrowTypeError: ("object of type <class 'str'> cannot be converted to int", 'Conversion failed for column 값 with type object')
```

의미:
- Streamlit의 `st.dataframe`(또는 `st.data_editor`)는 내부적으로 Pandas DataFrame을 **Arrow**로 변환해 프론트엔드에 전달합니다.
- 이때 특정 컬럼이 **혼합 타입(object)** 이고, Arrow가 **정수(int)로 예상한 타입에 문자열(str)이 섞여** 있으면 변환이 실패합니다.
- 변환 실패가 반복되면 화면 렌더링이 계속 막히거나(무한 로딩처럼 보임), 요청 처리 시간이 길어져 타임아웃으로 이어질 수 있습니다.

### 3-2. `use_container_width` 경고
로그:
```
Please replace `use_container_width` with `width`.
```
의미:
- 당장은 장애 원인은 아니고 **경고(warn)** 입니다.
- 다만 2025-12-31 이후 제거 예정이므로, 향후 Streamlit 업데이트 시 실제 오류로 바뀔 수 있습니다.

## 4) 원인 코드(추정 → 확인)
- **파일**: `modules/ui/tabs_daily.py`
- **구간**: "👤 수급자 정보" 영역에서 DataFrame 생성 시
  - 컬럼명: `값`
  - DataFrame 생성 후 `st.dataframe(df_customer, ...)` 호출

## 5) 적용한 해결

### 5-1. `값` 컬럼 타입을 문자열로 통일(Arrow 호환)
- **변경 파일**: `modules/ui/tabs_daily.py`
- **변경 내용**:
  - `customer_info_data.append({"항목": display_name, "값": str(value)})`
  - DataFrame 생성 후 `df_customer["값"] = df_customer["값"].astype(str)` 추가

의도:
- Arrow 변환이 실패하지 않도록 `값` 컬럼을 항상 문자열로 유지

## 6) 재발 방지 체크리스트
- **DataFrame 출력 전 타입 정규화**
  - 특히 `object` 타입 컬럼(혼합 타입) 주의
- **에러가 발생한 DataFrame 샘플을 로그로 남기기(최소)**
  - 컬럼명, dtype, 문제 값 1~2개 정도
- **Streamlit 경고(deprecated) 정리**
  - `use_container_width` → `width='stretch'` 점진적 치환

## 7) 운영 시 추천: 장애 시 즉시 확인 명령어
```bash
# 최근 로그
docker logs --tail 200 <container>

# 특정 시점 이후
docker logs --since "2026-02-22T05:50:00" <container>

# 리소스
docker stats <container>
```

---
작성일: 2026-02-22
