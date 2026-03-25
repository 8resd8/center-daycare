"""사이드바 UI 모듈 - 파일 업로드 및 선택

성능 최적화:
- 파일 처리 후 즉시 메모리 해제
- 캐시 무효화로 메모리 관리
- 세션 지속성을 위한 로컬스토리지 연동
"""

import gc
import time
import json
from datetime import date, datetime, timedelta
import streamlit as st
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from modules.pdf_parser import CareRecordParser
from modules.database import save_parsed_data, get_customers_with_records, get_all_records_by_date_range
from modules.ui.ui_helpers import (
    get_active_doc, get_person_keys_for_doc, iter_person_entries, 
    ensure_active_person, person_checkbox_key, select_person,
    get_person_done, set_person_done, invalidate_person_cache,
    iter_db_person_entries
)


def _get_current_month_range():
    """현재 달의 시작일과 종료일 반환"""
    today = date.today()
    first_day = today.replace(day=1)
    if today.month == 12:
        last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    return first_day, last_day


def _get_last_week_range():
    """저번주 월요일 ~ 일요일 반환"""
    today = date.today()
    # 오늘의 요일 (0=월, 6=일)
    current_weekday = today.weekday()
    # 이번주 월요일
    this_monday = today - timedelta(days=current_weekday)
    # 저번주 월요일
    last_monday = this_monday - timedelta(days=7)
    # 저번주 일요일
    last_sunday = last_monday + timedelta(days=6)
    return last_monday, last_sunday


def _restore_session_from_storage():
    """로컬스토리지에서 날짜 필터 복원 및 자동 조회"""
    if 'session_restored' not in st.session_state:
        st.session_state.session_restored = True
        st.session_state.auto_search_pending = True


def _check_auto_search():
    """새로고침 시 저장된 날짜로 자동 조회 실행"""
    if st.session_state.get('auto_search_pending') and not st.session_state.docs:
        st.session_state.auto_search_pending = False
        # 세션에 날짜가 있으면 자동 조회
        if st.session_state.get('db_filter_start') and st.session_state.get('db_filter_end'):
            start_date = st.session_state.db_filter_start
            end_date = st.session_state.db_filter_end
            _execute_db_search(start_date, end_date)


def _update_filter_from_parsed_data(parsed_data):
    """PDF 파싱 데이터에서 날짜 범위를 추출하여 필터에 반영"""
    if not parsed_data:
        return
    
    dates = []
    for record in parsed_data:
        record_date = record.get('date')
        if record_date:
            # 문자열이면 date로 변환
            if isinstance(record_date, str):
                try:
                    from datetime import datetime as dt
                    record_date = dt.strptime(record_date, '%Y-%m-%d').date()
                except:
                    continue
            dates.append(record_date)
    
    if dates:
        min_date = min(dates)
        max_date = max(dates)
        st.session_state['db_filter_start'] = min_date
        st.session_state['db_filter_end'] = max_date


def _save_session_to_storage():
    """세션 데이터를 로컬스토리지에 저장 (JavaScript 연동)"""
    # 날짜 필터 값 저장
    start_date = st.session_state.get('db_filter_start', '')
    end_date = st.session_state.get('db_filter_end', '')
    start_str = str(start_date) if start_date else ''
    end_str = str(end_date) if end_date else ''
    
    # 로컬스토리지에 날짜 필터 저장
    st.markdown(f"""
    <script>
    (function() {{
        localStorage.setItem('arisa_filter_start', '{start_str}');
        localStorage.setItem('arisa_filter_end', '{end_str}');
    }})();
    </script>
    """, unsafe_allow_html=True)


def render_sidebar():
    """사이드바 렌더링"""
    # 세션 복원 시도
    _restore_session_from_storage()
    
    # 자동 조회 체크 (새로고침 시)
    _check_auto_search()
    
    with st.sidebar:
        nav = st.radio(
            "메뉴",
            options=["파일 처리", "수급자 관리", "직원 관리", "대시보드"],
            index=0,
            horizontal=True,
            key="sidebar_nav_app",
        )
        if nav == "수급자 관리":
            st.switch_page("pages/customer_manage.py")
        elif nav == "직원 관리":
            st.switch_page("pages/employee_manage.py")
        elif nav == "대시보드":
            st.switch_page("pages/dashboard.py")

        st.header("📂 파일 처리")

        # 1. 파일 업로드 섹션
        uploaded_files = st.file_uploader(
            "장기요양급여 제공기록지 PDF 업로드",
            type=["pdf"],
            accept_multiple_files=True,
            key="pdf_uploader"
        )

        if uploaded_files:
            newly_added_id = None
            for f in uploaded_files:
                file_bytes = f.getvalue()
                # 파일 내용 기반 해시 생성 (중복 방지)
                file_id_source = f"{f.name}\0".encode("utf-8") + file_bytes
                file_id = hashlib.sha256(file_id_source).hexdigest()[:16]

                # 이미 존재하는 파일인지 확인
                exists = any(d.get("id") == file_id for d in st.session_state.docs)

                if not exists:
                    try:
                        # 파싱 시작 시간 기록
                        start_time = time.time()
                        status_placeholder = st.empty()
                        
                        # 백그라운드에서 파싱 실행
                        from concurrent.futures import ThreadPoolExecutor, wait
                        import threading
                        
                        parser = CareRecordParser(f)
                        parsed = None
                        parsing_done = threading.Event()
                        
                        def do_parse():
                            nonlocal parsed
                            parsed = parser.parse()
                            parsing_done.set()
                        
                        with ThreadPoolExecutor(max_workers=1) as executor:
                            future = executor.submit(do_parse)
                            
                            # 실시간 경과 시간 표시
                            while not parsing_done.is_set():
                                elapsed = time.time() - start_time
                                status_placeholder.info(f"📄 {f.name} 파싱 중... ({elapsed:.1f}초)")
                                time.sleep(0.5)
                            
                            future.result()  # 예외 발생 시 전파
                        
                        # 파싱 완료 시간 계산
                        elapsed_time = time.time() - start_time
                        total_records = len(parsed)
                        
                        # 완료 메시지 표시
                        status_placeholder.empty()
                        
                        # 파싱 후 파서 객체 해제
                        del parser
                        gc.collect()

                        new_doc = {
                            "id": file_id,
                            "name": f.name,
                            "completed": False,
                            "parsed_data": parsed,
                            "eval_results": {},
                            "error": None,
                        }
                        st.session_state.docs.append(new_doc)
                        newly_added_id = file_id
                        
                        # PDF 데이터에서 날짜 범위 추출하여 필터에 반영
                        _update_filter_from_parsed_data(parsed)
                        
                        # 파싱 완료 메시지를 session_state에 저장
                        st.session_state.parsing_success = f"{total_records}건 데이터 조회 ({elapsed_time:.1f}초)"

                    except Exception as e:
                        st.error(f"{f.name} 처리 중 오류: {e}")
                        st.session_state.docs.append({
                            "id": file_id,
                            "name": f.name,
                            "completed": False,
                            "parsed_data": [],
                            "error": str(e),
                        })

            # 새로 추가된 파일이 있으면 그 파일로 자동 전환
            if newly_added_id:
                st.session_state.active_doc_id = newly_added_id
                st.session_state.active_person_key = None
                st.rerun()

        # 파싱 완료 메시지 표시
        if 'parsing_success' in st.session_state:
            st.success(st.session_state.parsing_success)
            del st.session_state.parsing_success

        st.divider()
        
        # 📅 기간별 데이터 조회 - 항상 표시
        _render_date_filter_section()


        if st.session_state.docs:
            if not st.session_state.active_doc_id:
                st.session_state.active_doc_id = st.session_state.docs[0]["id"]

            active_doc = get_active_doc()
            
            # PDF 업로드된 경우에만 파일명 표시
            if active_doc and not active_doc.get('is_db_source'):
                st.subheader("📄 현재 파일")
                st.write(f"**{active_doc['name']}**")

            if active_doc and active_doc.get("parsed_data"):
                # Auto-save all parsed data to DB (only once)
                if not active_doc.get("db_saved"):
                    with st.spinner("DB 자동 저장 중..."):
                        count = save_parsed_data(active_doc["parsed_data"])
                        if count > 0:
                            st.toast(f"{count}건의 기록이 자동 저장되었습니다.", icon="✅")
                            for doc in st.session_state.docs:
                                if doc["id"] == active_doc["id"]:
                                    doc["db_saved"] = True
                                    break

            # Batch AI Processing buttons
            person_entries = iter_person_entries()
            if person_entries:
                st.divider()
                st.markdown("#### 기록지 AI 분석")
                
                st.markdown("""
                <style>
                .green-text {
                    color: #00C851 !important;
                }
                </style>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("주간상태변화 분석",
                               use_container_width=True, 
                               help="전체 인원의 주간 상태변화 기록지를 일괄 생성합니다"):
                        _batch_generate_weekly_reports(person_entries)
                with col2:
                    if st.button("일일 특이사항 평가",
                               use_container_width=True,
                               help="전체 인원의 특이사항을 일괄 평가합니다"):
                        _batch_evaluate_all_optimized(person_entries)

            # 프래그먼트로 사람 목록 렌더링 (부분 리렌더링 최적화)
            _render_person_list_fragment()
            
            # 세션 데이터 저장
            _save_session_to_storage()


@st.fragment
def _render_person_list_fragment():
    """사람 목록 렌더링 (프래그먼트로 부분 리렌더링 최적화)
    
    @st.fragment: 이 컴포넌트만 독립적으로 리렌더링되어 전체 페이지 새로고침 방지
    """
    person_entries = iter_person_entries()
    person_count = len(person_entries)
    st.subheader(f"👥 전체 {person_count}명")
    
    if not person_entries:
        st.info("파싱된 인원이 없습니다.")
        return
    
    st.caption("이름을 선택하면 상세 기록이 표시됩니다.")
    active_person_key = ensure_active_person()
    
    for entry in person_entries:
        is_active = entry["key"] == active_person_key
        cols = st.columns([0.75, 0.25])
        _pname = entry['person_name']
        try:
            from backend.encryption import mask_name as _mask
            _display_name = _pname[0] + "**" if _pname and len(_pname) > 0 else _pname
        except Exception:
            _display_name = _pname
        display_label = f"{_display_name} · {entry['record_count']}건"
        button_type = "primary" if is_active else "secondary"
        
        with cols[0]:
            if st.button(
                display_label,
                key=f"person_btn_{entry['key']}",
                type=button_type,
                use_container_width=True
            ):
                select_person(entry["key"], entry["doc_id"])
                st.rerun()
        
        with cols[1]:
            done_value = st.checkbox(
                "완료",
                value=get_person_done(entry["key"]),
                key=f"done_{entry['key']}"
            )
            set_person_done(entry["key"], done_value)


def _render_person_date_filter(entry):
    """선택된 대상자의 날짜 필터 렌더링"""
    person_name = entry.get('person_name', '대상자')
    
    with st.expander(f"📅 {person_name} 어르신 기간 필터", expanded=False):
        default_start, default_end = _get_current_month_range()
        
        # 대상자별 날짜 필터 세션 키
        person_start_key = f"person_filter_start_{entry['key']}"
        person_end_key = f"person_filter_end_{entry['key']}"
        
        if person_start_key not in st.session_state:
            st.session_state[person_start_key] = default_start
        if person_end_key not in st.session_state:
            st.session_state[person_end_key] = default_end
        
        col1, col2 = st.columns(2)
        with col1:
            p_start = st.date_input(
                "시작",
                value=st.session_state[person_start_key],
                key=f"p_start_{entry['key']}"
            )
        with col2:
            p_end = st.date_input(
                "종료",
                value=st.session_state[person_end_key],
                key=f"p_end_{entry['key']}"
            )
        
        st.session_state[person_start_key] = p_start
        st.session_state[person_end_key] = p_end
        
        if st.button(f"🔍 {person_name} 조회", use_container_width=True, key=f"p_search_{entry['key']}"):
            _execute_person_db_search(entry, p_start, p_end)


def _execute_person_db_search(entry, start_date, end_date):
    """특정 대상자의 DB 데이터 조회"""
    from modules.database import get_all_records_by_date_range
    
    person_name = entry.get('person_name')
    
    try:
        records = get_all_records_by_date_range(start_date, end_date)
        
        # 해당 대상자의 레코드만 필터링
        person_records = [r for r in records if r.get('customer_name') == person_name]
        
        if person_records:
            db_doc_id = f"db_person_{person_name}_{start_date}_{end_date}"
            
            # 기존 개인 조회 문서 제거
            st.session_state.docs = [d for d in st.session_state.docs 
                                      if not d.get('id', '').startswith(f'db_person_{person_name}_')]
            
            parsed_records = _convert_db_records(person_records)
            
            new_doc = {
                "id": db_doc_id,
                "name": f"{person_name} ({start_date} ~ {end_date})",
                "completed": False,
                "parsed_data": parsed_records,
                "eval_results": {},
                "error": None,
                "db_saved": True,
                "is_db_source": True,
            }
            st.session_state.docs.append(new_doc)
            st.session_state.active_doc_id = db_doc_id
            st.session_state.active_person_key = f"{db_doc_id}::{person_name}"
            
            invalidate_person_cache()
            
            st.toast(f"✅ {person_name} 어르신 {len(parsed_records)}건 조회", icon="✅")
            st.rerun()
        else:
            st.warning(f"해당 기간에 {person_name} 어르신의 기록이 없습니다.")
            
    except Exception as e:
        st.error(f"조회 오류: {e}")


def _batch_generate_weekly_reports(person_entries):
    """전체 인원의 주간 상태변화 기록지를 일괄 생성합니다."""
    if not person_entries:
        st.warning("처리할 인원이 없습니다.")
        return
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(person_entries)
    
    for i, entry in enumerate(person_entries):
        status_text.text(f"{entry['person_name']} 진행중 ({i+1}/{total})")
        
        # Get person records
        doc = next((d for d in st.session_state.docs if d["id"] == entry["doc_id"]), None)
        if not doc:
            continue
            
        person_records = [
            r for r in doc.get("parsed_data", [])
            if (r.get("customer_name") or "미상") == entry["person_name"]
        ]
        
        if not person_records:
            continue
            
        # Resolve customer_id
        from modules.customers import resolve_customer_id
        customer_id = (person_records[0].get("customer_id") if person_records else None)
        if customer_id is None:
            try:
                customer_id = resolve_customer_id(
                    name=entry["person_name"],
                    recognition_no=(person_records[0].get("customer_recognition_no") if person_records else None),
                    birth_date=(person_records[0].get("customer_birth_date") if person_records else None),
                )
            except Exception:
                customer_id = None
        
        if customer_id is None:
            continue
        
        # Compute weekly status
        from modules.weekly_data_analyzer import compute_weekly_status
        week_dates = sorted([r.get("date") for r in person_records if r.get("date")])
        if not week_dates:
            continue
            
        week_start = week_dates[-1]
        result = compute_weekly_status(entry["person_name"], week_start, customer_id)
        
        if result.get("error") or not result.get("scores"):
            continue
            
        # Generate AI report
        from modules.services.weekly_report_service import report_service
        from modules.database import save_weekly_status
        prev_range, curr_range = result["ranges"]
        ai_payload = result.get("trend", {}).get("ai_payload")
        
        if ai_payload:
            try:
                report = report_service.generate_weekly_report(
                    entry["person_name"],
                    (prev_range[0], curr_range[1]),
                    ai_payload,
                )
                
                if not isinstance(report, dict) or not report.get("error"):
                    text_report = report if isinstance(report, str) else str(report)
                    save_weekly_status(
                        customer_id=customer_id,
                        start_date=prev_range[0],
                        end_date=curr_range[1],
                        report_text=text_report,
                    )
            except Exception:
                pass
        
        progress_bar.progress((i + 1) / total)
    
    status_text.text("✅ 모든 인원의 주간 상태변화 기록지 생성이 완료되었습니다.")
    st.toast("✅ 일괄 처리 완료!", icon="✅")


def _batch_evaluate_all(person_entries):
    """전체 인원의 특이사항을 일괄 평가합니다."""
    if not person_entries:
        st.warning("처리할 인원이 없습니다.")
        return
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(person_entries)
    
    for i, entry in enumerate(person_entries):
        status_text.text(f"{entry['person_name']} 진행중 ({i+1}/{total})")
        
        # Get person records from database
        try:
            from modules.db_connection import db_query
            from modules.services.daily_report_service import evaluation_service
            
            with db_query() as cursor:
                # Get customer_id first
                cursor.execute(
                    "SELECT customer_id FROM customers WHERE name = %s LIMIT 1",
                    (entry["person_name"],)
                )
                customer_result = cursor.fetchone()
                
                if not customer_result:
                    continue
                    
                customer_id = customer_result["customer_id"]
                
                # Get records for this customer
                cursor.execute(
                    """
                    SELECT di.record_id, c.name as customer_name, di.date, 
                           dp.note as physical_note, dc.note as cognitive_note, 
                           dn.note as nursing_note, dr.note as functional_note,
                           dp.writer_name as writer_physical, dc.writer_name as writer_cognitive, 
                           dn.writer_name as writer_nursing, dr.writer_name as writer_recovery
                    FROM daily_infos di
                    LEFT JOIN customers c ON di.customer_id = c.customer_id
                    LEFT JOIN daily_physicals dp ON dp.record_id = di.record_id
                    LEFT JOIN daily_cognitives dc ON dc.record_id = di.record_id
                    LEFT JOIN daily_nursings dn ON dn.record_id = di.record_id
                    LEFT JOIN daily_recoveries dr ON dr.record_id = di.record_id
                    WHERE di.customer_id = %s
                    ORDER BY di.date DESC
                    """,
                    (customer_id,)
                )
                
                records = []
                for row in cursor.fetchall():
                    records.append({
                        "record_id": row["record_id"],
                        "customer_name": row["customer_name"],
                        "date": row["date"],
                        "physical_note": row["physical_note"],
                        "cognitive_note": row["cognitive_note"],
                        "nursing_note": row["nursing_note"],
                        "functional_note": row["functional_note"],
                        "writer_physical": row["writer_physical"],
                        "writer_cognitive": row["writer_cognitive"],
                        "writer_nursing": row["writer_nursing"],
                        "writer_recovery": row["writer_recovery"]
                    })
            
            # Evaluate all records for this person using process_daily_note_evaluation
            # 특이사항 평가는 PHYSICAL과 COGNITIVE만 수행
            for record in records:
                categories = [
                    ("PHYSICAL", record.get("physical_note", ""), record.get("writer_physical")),
                    ("COGNITIVE", record.get("cognitive_note", ""), record.get("writer_cognitive"))
                ]
                
                for category, text, category_writer in categories:
                    # 빈 텍스트는 건너뛰기
                    if not text or text.strip() in ['특이사항 없음', '결석', '']:
                        continue
                    
                    note_writer_id = record.get(f"writer_{category.lower()}_id", 1)
                    
                    evaluation_service.process_daily_note_evaluation(
                        record_id=record["record_id"],
                        category=category,
                        note_text=text,
                        note_writer_user_id=note_writer_id,
                        writer=category_writer or "",
                        customer_name=record.get("customer_name", ""),
                        date=record.get("date", "")
                    )
            
        except Exception as e:
            st.error(f"{entry['person_name']} 평가 중 오류: {e}")
        
        progress_bar.progress((i + 1) / total)
    
    status_text.text("✅ 모든 인원의 특이사항 평가가 완료되었습니다.")
    st.toast("✅ 일괄 평가 완료!", icon="✅")
    st.rerun()


def _batch_evaluate_all_optimized(person_entries):
    """성능 최적화된 전체 인원 특이사항 일괄 평가
    
    탭의 빠른 로직과 동일하게 evaluate_special_note_with_ai를 사용하여
    1번의 AI 호출로 신체/인지를 동시에 평가합니다.
    """
    if not person_entries:
        st.warning("처리할 인원이 없습니다.")
        return
    
    from modules.services.daily_report_service import evaluation_service
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 현재 active_doc에서 전체 레코드 수집
    active_doc = get_active_doc()
    if not active_doc or not active_doc.get("parsed_data"):
        st.warning("평가할 데이터가 없습니다.")
        return
    
    # 전체 인원 기록 수집 (탭과 동일한 로직)
    all_records = []
    for r in active_doc.get("parsed_data", []):
        if r.get("physical_note", "").strip() or r.get("cognitive_note", "").strip():
            # 이미 평가된 결과가 있는지 확인 (중복 요청 방지)
            customer_name = r.get('customer_name', '')
            date_str = r.get('date', '')
            record_id = evaluation_service.get_record_id(customer_name, date_str)
            
            # DB에서 이미 신체/인지 평가가 모두 있는지 확인
            if record_id:
                phys_eval = evaluation_service.get_evaluation_from_db(record_id, 'SPECIAL_NOTE_PHYSICAL')
                cogn_eval = evaluation_service.get_evaluation_from_db(record_id, 'SPECIAL_NOTE_COGNITIVE')
                
                # 이미 평가가 완료된 건은 제외
                if phys_eval['grade'] != '평가없음' and cogn_eval['grade'] != '평가없음':
                    continue
                    
            all_records.append(r)
    
    if not all_records:
        st.success("모든 기록이 이미 평가되었거나 평가할 특이사항이 없습니다.")
        return
    
    total = len(all_records)
    
    # 병렬 처리를 위한 함수 정의 (탭과 동일한 로직)
    def process_record(record):
        date_str = record.get("date", "날짜 없음")
        customer_name = record.get('customer_name', '')
        physical_note = record.get("physical_note", "").strip()
        cognitive_note = record.get("cognitive_note", "").strip()
        
        try:
            print(f"DEBUG: Processing {customer_name} ({date_str})")
            
            # 1번의 AI 호출로 신체/인지 동시 평가
            result = evaluation_service.evaluate_special_note_with_ai(record)
            if result:
                record_id = evaluation_service.get_record_id(customer_name, date_str)
                if record_id:
                    result_with_notes = result.copy()
                    result_with_notes['physical_note'] = physical_note
                    result_with_notes['cognitive_note'] = cognitive_note
                    evaluation_service.save_special_note_evaluation(record_id, result_with_notes)
            return True
        except Exception as e:
            print(f"Error processing {customer_name} ({date_str}): {str(e)}")
            return False

    max_workers = 4
    completed = 0
    
    # UI 업데이트용 컨테이너
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_record = {executor.submit(process_record, rec): rec for rec in all_records}
        for future in concurrent.futures.as_completed(future_to_record):
            try:
                future.result(timeout=40)
            except concurrent.futures.TimeoutError:
                print("DEBUG: Task timed out")
            except Exception as e:
                print(f"DEBUG: Task error: {e}")
            
            completed += 1
            progress_bar.progress(completed / total)
            status_text.text(f"⏳ 전체 인원 평가 진행 중... ({completed}/{total})")
    
    st.success(f"총 {total}건의 특이사항 평가가 완료되었습니다.")
    st.toast("✅ 일괄 평가 완료!", icon="✅")
    st.rerun()


def _render_date_filter_section():
    """📅 기간별 데이터 조회 섹션 - 항상 표시"""
    st.subheader("📅 기간별 데이터 조회")
    
    # 날짜 필터링 (디폴트: 현재 달)
    default_start, default_end = _get_current_month_range()
    
    # 위젯 키
    start_key = "db_filter_start"
    end_key = "db_filter_end"
    
    # 초기값 설정
    if start_key not in st.session_state:
        st.session_state[start_key] = default_start
    if end_key not in st.session_state:
        st.session_state[end_key] = default_end
    
    # 버튼 클릭 플래그 확인 및 값 변경 (위젯 생성 전)
    if st.session_state.get('_set_last_week'):
        last_mon, last_sun = _get_last_week_range()
        st.session_state[start_key] = last_mon
        st.session_state[end_key] = last_sun
        del st.session_state['_set_last_week']
    
    if st.session_state.get('_set_prev_week'):
        current_start = st.session_state[start_key]
        current_monday = current_start - timedelta(days=current_start.weekday())
        prev_monday = current_monday - timedelta(days=7)
        prev_sunday = prev_monday + timedelta(days=6)
        st.session_state[start_key] = prev_monday
        st.session_state[end_key] = prev_sunday
        del st.session_state['_set_prev_week']
    
    col1, col2 = st.columns(2)
    with col1:
        st.date_input("시작일", key=start_key)
    with col2:
        st.date_input("종료일", key=end_key)
    
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button("조회", use_container_width=True, key="db_search_btn"):
            _execute_db_search(st.session_state[start_key], st.session_state[end_key])
    with col_btn2:
        if st.button("1주전", use_container_width=True, key="db_prev_week_btn"):
            st.session_state['_set_prev_week'] = True
            st.rerun()
    with col_btn3:
        if st.button("지난주", use_container_width=True, key="db_last_week_btn"):
            st.session_state['_set_last_week'] = True
            st.rerun()

    # 현재 조회된 기간 표시
    if st.session_state.get('db_records_loaded'):
        active_doc = get_active_doc()
        if active_doc and active_doc.get('is_db_source'):
            record_count = len(active_doc.get('parsed_data', []))
            st.caption(f"전체 데이터 개수: {record_count}건")


def _execute_db_search(start_date, end_date):
    """DB에서 전체 데이터 조회 실행"""
    try:
        records = get_all_records_by_date_range(start_date, end_date)
        
        if records:
            db_doc_id = f"db_{start_date}_{end_date}"
            
            # 기존 DB 문서가 있으면 제거
            st.session_state.docs = [d for d in st.session_state.docs if not d.get('id', '').startswith('db_')]
            
            # DB 레코드를 parsed_data 형식으로 변환
            parsed_records = _convert_db_records(records)
            
            new_doc = {
                "id": db_doc_id,
                "name": f"DB 조회 ({start_date} ~ {end_date})",
                "completed": False,
                "parsed_data": parsed_records,
                "eval_results": {},
                "error": None,
                "db_saved": True,
                "is_db_source": True,
            }
            st.session_state.docs.append(new_doc)
            st.session_state.active_doc_id = db_doc_id
            st.session_state.active_person_key = None
            st.session_state.db_records_loaded = True
            
            # 캐시 무효화
            invalidate_person_cache()
            
            st.toast(f"✅ {len(parsed_records)}건의 기록을 조회했습니다.", icon="✅")
            st.rerun()
        else:
            st.toast(f"{start_date} ~ {end_date} 기록이 없습니다.", icon="ℹ️")
            
    except Exception as e:
        st.error(f"데이터 조회 중 오류: {e}")


def _convert_db_records(records):
    """DB 레코드를 parsed_data 형식으로 변환"""
    parsed_records = []
    for r in records:
        parsed_records.append({
            'customer_id': r.get('customer_id'),
            'customer_name': r.get('customer_name'),
            'customer_birth_date': r.get('customer_birth_date'),
            'customer_grade': r.get('customer_grade'),
            'customer_recognition_no': r.get('customer_recognition_no'),
            'record_id': r.get('record_id'),
            'date': r.get('date'),
            'start_time': r.get('start_time'),
            'end_time': r.get('end_time'),
            'total_service_time': r.get('total_service_time'),
            'transport_service': r.get('transport_service'),
            'transport_vehicles': r.get('transport_vehicles'),
            'hygiene_care': r.get('hygiene_care'),
            'bath_time': r.get('bath_time'),
            'bath_method': r.get('bath_method'),
            'meal_breakfast': r.get('meal_breakfast'),
            'meal_lunch': r.get('meal_lunch'),
            'meal_dinner': r.get('meal_dinner'),
            'toilet_care': r.get('toilet_care'),
            'mobility_care': r.get('mobility_care'),
            'physical_note': r.get('physical_note'),
            'writer_phy': r.get('writer_phy'),
            'cog_support': r.get('cog_support'),
            'comm_support': r.get('comm_support'),
            'cognitive_note': r.get('cognitive_note'),
            'writer_cog': r.get('writer_cog'),
            'bp_temp': r.get('bp_temp'),
            'health_manage': r.get('health_manage'),
            'nursing_manage': r.get('nursing_manage'),
            'emergency': r.get('emergency'),
            'nursing_note': r.get('nursing_note'),
            'writer_nur': r.get('writer_nur'),
            'prog_basic': r.get('prog_basic'),
            'prog_activity': r.get('prog_activity'),
            'prog_cognitive': r.get('prog_cognitive'),
            'prog_therapy': r.get('prog_therapy'),
            'prog_enhance_detail': r.get('prog_enhance_detail'),
            'functional_note': r.get('functional_note'),
            'writer_func': r.get('writer_func'),
        })
    return parsed_records
