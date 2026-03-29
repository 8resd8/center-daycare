"""기록 조회 탭 UI 모듈"""

import streamlit as st
import pandas as pd
import hashlib
import json
import time
from datetime import date, timedelta
import streamlit.components.v1 as components
from modules.database import save_weekly_status, load_weekly_status, get_all_records_by_date_range
from modules.customers import resolve_customer_id
from modules.weekly_data_analyzer import compute_weekly_status
from modules.services.weekly_report_service import report_service
from modules.ui.ui_helpers import get_active_doc, get_active_person_records, invalidate_person_cache
from modules.utils.enums import CategoryDisplay, RequiredFields, WriterFields, WeeklyDisplayFields


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
    """지난주 월요일 ~ 일요일 반환"""
    today = date.today()
    current_weekday = today.weekday()
    this_monday = today - timedelta(days=current_weekday)
    last_monday = this_monday - timedelta(days=7)
    last_sunday = last_monday + timedelta(days=6)
    return last_monday, last_sunday


def render_records_tab():
    """기록 조회 탭 렌더링"""
    doc_ctx, person_name, person_records = get_active_person_records()
    active_doc = doc_ctx or get_active_doc()

    if not active_doc:
        st.warning("👈 왼쪽 사이드바에서 파일을 선택하거나 업로드해주세요.")
    elif active_doc.get("error"):
        st.error(f"이 파일은 파싱 중 오류가 발생했습니다: {active_doc['error']}")
    elif not person_records:
        st.warning("선택된 어르신의 데이터가 없습니다.")
    else:
        data = person_records
        customer_name = person_name or (data[0].get('customer_name', '알 수 없음') if data else '알 수 없음')

        st.markdown(f"### 👤 대상자: **{customer_name}** 어르신")
        
        # 대상자별 날짜 필터
        _render_person_date_filter(customer_name, active_doc)

        sub_tab_basic, sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(CategoryDisplay.WEEKLY_DISPLAY_NAMES)

        with sub_tab_basic:
            df_basic = pd.DataFrame([{
                display_name: r.get(field_name, "-" if field_name != "transport_service" else "미제공")
                for display_name, field_name in WeeklyDisplayFields.BASIC_INFO_DISPLAY.items()
            } for r in data])
            st.dataframe(df_basic, use_container_width=True, hide_index=True)

        with sub_tab1:
            df_phy = pd.DataFrame([{
                "날짜": r.get('date'),
                "특이사항": r.get('physical_note'),
                "세면/구강": r.get('hygiene_care'),
                "목욕": r.get('bath_time') if r.get('bath_time') == "없음" else f"{r.get('bath_time')} / {r.get('bath_method')}",
                "식사": f"{r.get('meal_breakfast') or ''}{r.get('meal_lunch') and ('/' + r.get('meal_lunch')) or ''}{r.get('meal_dinner') and ('/' + r.get('meal_dinner')) or ''}",
                "화장실이용하기(기저귀교환)": r.get('toilet_care'),
                "이동": r.get('mobility_care'),
                "작성자": r.get('writer_phy')
            } for r in data])
            st.dataframe(df_phy, use_container_width=True, hide_index=True)

        with sub_tab2:
            df_cog = pd.DataFrame([{
                display_name: r.get(field_name)
                for display_name, field_name in WeeklyDisplayFields.COGNITIVE_CARE_DISPLAY.items()
            } for r in data])
            st.dataframe(df_cog, use_container_width=True, hide_index=True)

        with sub_tab3:
            df_nur = pd.DataFrame([{
                display_name: r.get(field_name)
                for display_name, field_name in WeeklyDisplayFields.NURSING_CARE_DISPLAY.items()
            } for r in data])
            st.dataframe(df_nur, use_container_width=True, hide_index=True)

        with sub_tab4:
            df_func = pd.DataFrame([{
                display_name: r.get(field_name)
                for display_name, field_name in WeeklyDisplayFields.FUNCTIONAL_RECOVERY_DISPLAY.items()
            } for r in data])
            st.dataframe(df_func, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("#### 📈 주간 상태 변화")
        
        # 필터 시작일을 주간 분석 기준으로 사용
        safe_name = customer_name.replace(" ", "_")
        filter_start_key = f"main_p_start_{safe_name}"
        filter_start = st.session_state.get(filter_start_key)
        
        if filter_start:
            # 필터 시작일을 문자열로 변환
            if isinstance(filter_start, date):
                week_start = filter_start.strftime("%Y-%m-%d")
            else:
                week_start = str(filter_start)
            
            # Resolve customer_id before using it
            customer_id = (data[0].get("customer_id") if data else None)
            if customer_id is None:
                try:
                    customer_id = resolve_customer_id(
                        name=customer_name,
                        recognition_no=(data[0].get("customer_recognition_no") if data else None),
                        birth_date=(data[0].get("customer_birth_date") if data else None),
                    )
                except Exception:
                    customer_id = None
            
            result = compute_weekly_status(customer_name, week_start, customer_id)
            if result.get("error"):
                st.error(f"주간 분석 실패: {result['error']}")
            elif not result.get("scores"):
                st.info("주간 비교 데이터가 충분하지 않습니다.")
            else:
                prev_range, curr_range = result["ranges"]
                st.caption(
                    f"전주: {prev_range[0]} ~ {prev_range[1]} / "
                    f"이번주: {curr_range[0]} ~ {curr_range[1]}"
                )
                trend = result.get("trend") or {}
                header = trend.get("header") or {}
                weekly_table = trend.get("weekly_table") or []
                if weekly_table:
                    st.dataframe(
                        pd.DataFrame(weekly_table),
                        use_container_width=True,
                        hide_index=True,
                    )

                else:
                    st.info("주간 상태 변화 표를 생성할 수 없습니다.")
                st.divider()
                st.markdown("#### 🔍 지난주 vs 이번주 핵심 지표")
                header_cols = st.columns(2)
                def _format_ratio(value):
                    if value is None:
                        return "-"
                    try:
                        return f"{value:.2f}"
                    except Exception:
                        return "-"

                meal_header = header.get("meal_amount", {})
                header_cols[0].metric(
                    label="식사량 (출석당 평균)",
                    value=_format_ratio(meal_header.get("curr")),
                    delta=meal_header.get("change_label", "데이터 부족"),
                    delta_color="normal",
                )
                toilet_header = header.get("toilet", {})
                header_cols[1].metric(
                    label="배설 (출석당 평균)",
                    value=_format_ratio(toilet_header.get("curr")),
                    delta=toilet_header.get("change_label", "데이터 부족"),
                    delta_color="inverse",
                )
                ai_payload = trend.get("ai_payload")
                if ai_payload:
                    st.divider()
                    st.markdown("#### 주간 상태변화 기록지 생성")
                    ai_col, result_col = st.columns([1, 3])
                    progress_bar = ai_col.empty()
                    status_line = ai_col.empty()
                    response_area = result_col.container()

                    person_key = st.session_state.get("active_person_key")
                    report_identity = str(customer_id) if customer_id is not None else (person_key or customer_name)
                    report_state_key = f"weekly_ai_report::{report_identity}::{prev_range[0]}::{curr_range[1]}"
                    # Add timestamp to widget key to ensure uniqueness
                    widget_key = f"weekly_ai_report_widget::{report_identity}::{prev_range[0]}::{curr_range[1]}::{int(time.time())}"

                    if report_state_key not in st.session_state:
                        saved_report = None
                        if customer_id is not None:
                            try:
                                saved_report = load_weekly_status(
                                    customer_id=customer_id,
                                    start_date=prev_range[0],
                                    end_date=curr_range[1],
                                )
                            except Exception:
                                saved_report = None
                        if saved_report:
                            st.session_state[report_state_key] = saved_report

                    if st.session_state.get(report_state_key):
                        _render_copyable_report(
                            response_area,
                            st.session_state.get(report_state_key, ""),
                            report_state_key,
                            widget_key,
                        )
                    if ai_col.button("생성하기"):
                        progress_bar.progress(0)
                        status_line.text("요청 중... 0%")
                        try:
                            progress_bar.progress(15)
                            status_line.text("상태변화 기록지 생성중... 15%")
                            report = report_service.generate_weekly_report(
                                customer_name,
                                (prev_range[0], curr_range[1]),
                                ai_payload,
                            )
                            progress_bar.progress(60)
                            status_line.text("보고서 생성 중... 60%")
                            if isinstance(report, dict) and report.get("error"):
                                response_area.error(report["error"])
                            else:
                                text_report = report if isinstance(report, str) else str(report)
                                st.session_state[report_state_key] = text_report
                                if customer_id is not None:
                                    try:
                                        save_weekly_status(
                                            customer_id=customer_id,
                                            start_date=prev_range[0],
                                            end_date=curr_range[1],
                                            report_text=text_report,
                                        )
                                    except Exception:
                                        pass
                                # Use st.rerun() to re-render the report via the first call path
                                st.rerun()
                            progress_bar.progress(100)
                            status_line.text("완료: 100%")
                        except Exception as exc:
                            progress_bar.progress(0)
                            status_line.error(f"요청 실패: {exc}")
        else:
            st.info("주간 비교를 위한 날짜 정보가 부족합니다.")


def _render_copyable_report(container, text: str, state_key: str, widget_key: str):
    """주간 AI 결과를 세션에 유지되는 텍스트로 렌더링합니다."""
    if state_key not in st.session_state:
        st.session_state[state_key] = text or ""

    if not st.session_state.get(state_key):
        container.info("표시할 AI 결과가 없습니다.")
        return

    # Use widget_key for the text_area to avoid session_state modification error
    container.text_area("AI 보고서", key=widget_key, height=220, value=st.session_state[state_key])

    element_id = hashlib.md5(state_key.encode("utf-8")).hexdigest()
    js_text = json.dumps(st.session_state.get(state_key, ""))
    components.html(
        f"""
        <div style="margin-top: 8px; display:flex; gap:12px; align-items:center;">
          <button id="copy_{element_id}" style="padding:6px 12px; border-radius:6px; border:1px solid #d0d7de; background:#ffffff; cursor:pointer;">복사하기</button>
          <span id="copy_tip_{element_id}" style="font-size:12px; color:#57606a;"></span>
        </div>
        <script>
          (function() {{
            const btn = document.getElementById('copy_{element_id}');
            const tip = document.getElementById('copy_tip_{element_id}');
            if (!btn || btn.dataset.bound) return;
            btn.dataset.bound = '1';
            btn.addEventListener('click', async () => {{
              try {{
                await navigator.clipboard.writeText({js_text});
                if (tip) tip.textContent = '복사 완료';
              }} catch (e) {{
                if (tip) tip.textContent = '복사 실패: 브라우저 권한을 확인해주세요.';
              }}
            }});
          }})();
        </script>
        """,
        height=40,
    )


def _render_person_date_filter(customer_name: str, active_doc):
    """대상자별 날짜 필터 렌더링 (메인화면)"""
    default_start, default_end = _get_current_month_range()

    # 위젯 키
    safe_name = customer_name.replace(" ", "_")
    start_key = f"main_p_start_{safe_name}"
    end_key = f"main_p_end_{safe_name}"

    # PDF 업로드 데이터에서 날짜 범위 추출
    pdf_start, pdf_end = _get_date_range_from_doc(active_doc, customer_name)
    
    # 초기값 설정 (PDF 날짜가 있으면 우선 사용)
    if start_key not in st.session_state:
        st.session_state[start_key] = pdf_start if pdf_start else default_start
    if end_key not in st.session_state:
        st.session_state[end_key] = pdf_end if pdf_end else default_end
    
    # PDF 문서가 변경되었을 때 필터 업데이트
    doc_id_key = f"_last_doc_id_{safe_name}"
    current_doc_id = active_doc.get('id') if active_doc else None
    if current_doc_id and st.session_state.get(doc_id_key) != current_doc_id:
        if pdf_start and pdf_end:
            st.session_state[start_key] = pdf_start
            st.session_state[end_key] = pdf_end
        st.session_state[doc_id_key] = current_doc_id

    # 버튼 클릭 플래그 확인 및 값 변경 (위젯 생성 전)
    last_week_flag = f"_set_last_week_{safe_name}"
    prev_week_flag = f"_set_prev_week_{safe_name}"
    
    if st.session_state.get(last_week_flag):
        last_mon, last_sun = _get_last_week_range()
        st.session_state[start_key] = last_mon
        st.session_state[end_key] = last_sun
        del st.session_state[last_week_flag]
    
    if st.session_state.get(prev_week_flag):
        current_start = st.session_state[start_key]
        current_monday = current_start - timedelta(days=current_start.weekday())
        prev_monday = current_monday - timedelta(days=7)
        prev_sunday = prev_monday + timedelta(days=6)
        st.session_state[start_key] = prev_monday
        st.session_state[end_key] = prev_sunday
        del st.session_state[prev_week_flag]

    # 해당 인원 필터 조회
    col1, col2 = st.columns(2)
    with col1:
        st.date_input("시작", key=start_key)
    with col2:
        st.date_input("종료", key=end_key)

    # 버튼: 조회 | 지난주 | 1주전
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button(f"조회", use_container_width=True, key=f"main_p_search_{safe_name}"):
            _execute_person_search(customer_name, st.session_state[start_key], st.session_state[end_key])
    with col_btn2:
        if st.button(f"1주전", use_container_width=True, key=f"main_p_prevweek_{safe_name}"):
            st.session_state[prev_week_flag] = True
            st.rerun()
    with col_btn3:
        if st.button(f"지난주", use_container_width=True, key=f"main_p_lastweek_{safe_name}"):
            st.session_state[last_week_flag] = True
            st.rerun()

def _execute_person_search(customer_name: str, start_date, end_date):
    """특정 대상자의 DB 데이터 조회"""
    try:
        records = get_all_records_by_date_range(start_date, end_date)
        
        # 해당 대상자의 레코드만 필터링
        person_records = [r for r in records if r.get('customer_name') == customer_name]
        
        if person_records:
            db_doc_id = f"db_person_{customer_name}_{start_date}_{end_date}"
            
            # 기존 개인 조회 문서 제거
            st.session_state.docs = [d for d in st.session_state.docs 
                                      if not d.get('id', '').startswith(f'db_person_{customer_name}_')]
            
            # DB 레코드를 parsed_data 형식으로 변환
            parsed_records = _convert_db_records(person_records)
            
            new_doc = {
                "id": db_doc_id,
                "name": f"{customer_name} ({start_date} ~ {end_date})",
                "completed": False,
                "parsed_data": parsed_records,
                "eval_results": {},
                "error": None,
                "db_saved": True,
                "is_db_source": True,
            }
            st.session_state.docs.append(new_doc)
            st.session_state.active_doc_id = db_doc_id
            st.session_state.active_person_key = f"{db_doc_id}::{customer_name}"
            
            invalidate_person_cache()
            
            st.toast(f"✅ {customer_name} 어르신 {len(parsed_records)}건 조회", icon="✅")
            st.rerun()
        else:
            st.toast(f"{start_date} ~ {end_date} 기록이 없습니다.", icon="ℹ️")
            
    except Exception as e:
        st.error(f"조회 오류: {e}")


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


def _get_date_range_from_doc(active_doc, customer_name):
    """PDF 문서에서 특정 대상자의 날짜 범위 추출"""
    if not active_doc or not active_doc.get('parsed_data'):
        return None, None
    
    dates = []
    for record in active_doc['parsed_data']:
        # 해당 대상자의 레코드만 필터링
        if record.get('customer_name') == customer_name:
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
        return min(dates), max(dates)
    return None, None
