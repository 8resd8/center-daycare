"""기록 조회 탭 UI 모듈"""

import streamlit as st
import pandas as pd
import hashlib
import json
import time
import streamlit.components.v1 as components
from modules.database import save_weekly_status, load_weekly_status
from modules.customers import resolve_customer_id
from modules.weekly_data_analyzer import compute_weekly_status
from modules.ai_weekly_writer import generate_weekly_report
from modules.ui.ui_helpers import get_active_doc, get_active_person_records


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

        sub_tab_basic, sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
            "ℹ️ 기본 정보", "💪 신체활동지원", "🧠 인지관리", "🩺 간호관리", "🏃 기능회복"
        ])

        with sub_tab_basic:
            df_basic = pd.DataFrame([{
                "날짜": r.get('date'),
                "총시간": r.get('total_service_time', "-"),
                "시작시간": r.get('start_time') or "-",
                "종료시간": r.get('end_time') or "-",
                "이동서비스": r.get('transport_service', "미제공"),
                "차량번호": r.get('transport_vehicles', "")
            } for r in data])
            st.dataframe(df_basic, use_container_width=True, hide_index=True)

        with sub_tab1:
            df_phy = pd.DataFrame([{
                "날짜": r.get('date'),
                "특이사항": r.get('physical_note'),
                "세면/구강": r.get('hygiene_care'),
                "목욕": r.get('bath_time') if r.get('bath_time') == "없음" else f"{r.get('bath_time')} / {r.get('bath_method')}",
                "식사": f"{r.get('meal_breakfast')}/{r.get('meal_lunch')}/{r.get('meal_dinner')}",
                "화장실이용하기(기저귀교환)": r.get('toilet_care'),
                "이동": r.get('mobility_care'),
                "작성자": r.get('writer_phy')
            } for r in data])
            st.dataframe(df_phy, use_container_width=True, hide_index=True)

        with sub_tab2:
            df_cog = pd.DataFrame([{
                "날짜": r.get('date'),
                "특이사항": r.get('cognitive_note'),
                "인지관리지원": r.get('cog_support'),
                "의사소통도움": r.get('comm_support'),
                "작성자": r.get('writer_cog')
            } for r in data])
            st.dataframe(df_cog, use_container_width=True, hide_index=True)

        with sub_tab3:
            df_nur = pd.DataFrame([{
                "날짜": r.get('date'),
                "특이사항": r.get('nursing_note'),
                "혈압/체온": r.get('bp_temp'),
                "건강관리(5분)": r.get('health_manage'),
                "간호관리": r.get('nursing_manage'),
                "응급서비스": r.get('emergency'),
                "작성자": r.get('writer_nur')
            } for r in data])
            st.dataframe(df_nur, use_container_width=True, hide_index=True)

        with sub_tab4:
            df_func = pd.DataFrame([{
                "날짜": r.get('date'),
                "특이사항": r.get('functional_note'),
                "향상 프로그램 내용": r.get('prog_enhance_detail'),
                "향상 프로그램 여부": r.get('prog_basic'),
                "인지활동 프로그램": r.get('prog_activity'),
                "인지기능 훈련": r.get('prog_cognitive'),
                "물리치료": r.get('prog_therapy'),
                "작성자": r.get('writer_func')
            } for r in data])
            st.dataframe(df_func, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("#### 📈 주간 상태 변화")
        week_dates = sorted([r.get("date") for r in data if r.get("date")])
        if week_dates:
            week_start = week_dates[-1]
            
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
                            report = generate_weekly_report(
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
