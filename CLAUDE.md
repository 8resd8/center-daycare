# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language

모든 응답은 한국어로 작성하세요.

## Project Overview

보은사랑 기록 관리 시스템 — a Streamlit-based internal tool for long-term care (요양) facilities. It parses care record PDFs, stores daily records in MySQL, and uses AI (Google Gemini / OpenAI GPT) to evaluate and generate weekly status reports.

## Commands

### Run the app (development)
```bash
run app.py --server.enableCORS=false --server.enableXsrfProtection=false --browser.serverAddress=localhost --browser.serverPort=8501
```

### Run tests
```bash
pytest                          # all tests
pytest tests/repositories/      # repository tests only
pytest tests/services/          # service tests only
pytest -k test_name             # single test by name
pytest --cov=modules            # with coverage
```

### Docker
```bash
# Development
docker-compose up --build

# Production
docker-compose -f docker-compose.prod.yml up -d
```

### Install dependencies
```bash
pip install -r requirements.txt
```

## Architecture

### Entry Point & Pages
- `app.py` — main entry, sets up the Streamlit page with two tabs (주간 상태 변화 평가 / 일일 특이사항 평가) and a sidebar nav
- `pages/customer_manage.py` — 수급자 CRUD
- `pages/employee_manage.py` — 직원 CRUD
- `pages/dashboard.py` — analytics dashboard using Altair charts; uses `@st.cache_data(ttl=300)` for data loading

### Module Structure (`modules/`)

```
modules/
├── ui/                    # Streamlit UI components
│   ├── sidebar.py         # PDF upload, date filter, person list
│   ├── tabs_weekly.py     # 주간 상태 변화 평가 tab
│   ├── tabs_daily.py      # 일일 특이사항 평가 tab
│   └── ui_helpers.py      # Shared session_state helpers
├── repositories/          # Data access layer (extends BaseRepository)
│   ├── base.py            # _execute_query / _execute_transaction helpers
│   ├── customer.py
│   ├── daily_info.py
│   ├── weekly_status.py
│   ├── ai_evaluation.py
│   ├── employee_evaluation.py
│   └── user.py
├── services/              # Business logic layer
│   ├── daily_report_service.py   # AI evaluation of daily notes
│   ├── weekly_report_service.py  # AI weekly report generation
│   └── analytics_service.py     # Wraps weekly_data_analyzer functions
├── clients/               # External API wrappers
│   ├── ai_client.py       # OpenAIClient / GeminiClient (BaseAIClient)
│   ├── daily_prompt.py    # Prompt templates for daily evaluation
│   └── weekly_prompt.py   # Prompt templates for weekly reports
├── db_connection.py       # MySQL connection pool + db_query/db_transaction context managers
├── database.py            # Thin facade over repositories (legacy compatibility)
├── pdf_parser.py          # CareRecordParser — extracts structured data from PDF care records
├── weekly_data_analyzer.py # Score/trend computation for weekly reports
├── customers.py           # resolve_customer_id helper
└── analytics.py           # Microsoft Clarity injection
```

### Database Connection Pattern
- `db_connection.py` provides two context managers:
  - `db_query()` — read-only, dictionary cursor, unbuffered
  - `db_transaction()` — write operations, auto-commit/rollback
- Config priority: env vars (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT`) → Streamlit secrets (`[mysql]` section in `.streamlit/secrets.toml`)
- Connection pooling via `mysql.connector.pooling.MySQLConnectionPool`

### AI Client Pattern
- `get_ai_client(provider='gemini')` returns a `BaseAIClient` instance
- API key priority: env vars (`GEMINI_API_KEY` / `OPENAI_API_KEY`) → Streamlit secrets
- In Streamlit runtime, clients are cached via `@st.cache_resource`
- Rate limits handled by `tenacity` retry decorator (5 attempts, exponential backoff)

### Testing Strategy
Tests live in `tests/` mirroring `modules/` structure. All DB and AI calls are mocked:
- `conftest.py` provides `MockCursor`, `MockConnection`, `MockAIClient` and pytest fixtures `mock_db`, `mock_db_query`, `mock_db_transaction`
- To inject a mock DB: use `mock_db` fixture which patches both `db_query` and `db_transaction`
- To inject a mock AI client: call `set_ai_client(mock_client)` from `modules.clients.ai_client`, clean up with `set_ai_client(None)` in teardown

### Session State Conventions
Key session state variables in `app.py`:
- `st.session_state.docs` — list of document dicts (parsed PDFs or DB query results)
- `st.session_state.active_doc_id` — currently selected document
- `st.session_state.active_person_key` — `"{doc_id}::{person_name}"` format
- `st.session_state.ai_suggestion_tables` — cached AI evaluation results

Documents loaded from DB have `is_db_source: True` and `db_saved: True` flags.