"""📊 대시보드 - 종합 분석 화면"""

import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from modules.db_connection import get_db_connection

# --- 페이지 설정 ---
st.set_page_config(page_title="대시보드", layout="wide", page_icon="📊")

# --- 스타일링 ---
st.markdown("""
<style>
    .stDeployButton {display:none;}
    h1 { margin-bottom: 1rem; }
    [data-testid="stSidebarNav"] { display: none; }
    
    /* KPI 카드 스타일 */
    [data-testid="stMetric"] {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        color: #666;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# --- 데이터 로드 함수 ---
@st.cache_data(ttl=300)
def load_dashboard_data(start_date: date, end_date: date) -> dict:
    """대시보드에 필요한 모든 데이터를 한 번에 로드"""
    conn = get_db_connection()
    
    # 1. 직원 평가 데이터 (employee_evaluations)
    emp_eval_query = """
        SELECT 
            ee.emp_eval_id,
            ee.record_id,
            ee.target_user_id,
            ee.evaluator_user_id,
            ee.category,
            ee.evaluation_type,
            ee.score,
            ee.comment,
            ee.evaluation_date,
            ee.created_at,
            u.name AS target_user_name,
            u.work_status
        FROM employee_evaluations ee
        LEFT JOIN users u ON ee.target_user_id = u.user_id
        WHERE ee.evaluation_date BETWEEN %s AND %s
    """
    df_emp_eval = pd.read_sql(emp_eval_query, conn, params=(start_date, end_date))
    
    # 2. AI 평가 데이터 (ai_evaluations)
    ai_eval_query = """
        SELECT 
            ae.ai_eval_id,
            ae.record_id,
            ae.category,
            ae.grade_code,
            ae.oer_fidelity,
            ae.specificity_score,
            ae.grammar_score,
            ae.created_at,
            di.date AS evaluation_date,
            di.customer_id
        FROM ai_evaluations ae
        JOIN daily_infos di ON ae.record_id = di.record_id
        WHERE di.date BETWEEN %s AND %s
    """
    df_ai_eval = pd.read_sql(ai_eval_query, conn, params=(start_date, end_date))
    
    # 3. 재직 중인 직원 목록
    users_query = """
        SELECT user_id, name, work_status
        FROM users
        WHERE work_status = '재직'
        ORDER BY name
    """
    df_users = pd.read_sql(users_query, conn)
    
    # 4. 전월 데이터 (전월 대비 계산용)
    prev_month_start = (datetime.combine(start_date, datetime.min.time()) - relativedelta(months=1)).replace(day=1).date()
    prev_month_end = (datetime.combine(start_date, datetime.min.time()) - timedelta(days=1)).date()
    
    prev_emp_eval_query = """
        SELECT COUNT(*) as count
        FROM employee_evaluations
        WHERE evaluation_date BETWEEN %s AND %s
    """
    df_prev_count = pd.read_sql(prev_emp_eval_query, conn, params=(prev_month_start, prev_month_end))
    
    conn.close()
    
    return {
        "emp_eval": df_emp_eval,
        "ai_eval": df_ai_eval,
        "users": df_users,
        "prev_month_count": df_prev_count['count'].iloc[0] if not df_prev_count.empty else 0
    }


def get_unique_values(df: pd.DataFrame, column: str) -> list:
    """데이터프레임에서 고유값 목록 추출"""
    if df.empty or column not in df.columns:
        return []
    return sorted(df[column].dropna().unique().tolist())


# --- 사이드바 ---
with st.sidebar:
    # 네비게이션 메뉴
    nav = st.radio(
        "메뉴",
        options=["파일 처리", "수급자 관리", "대시보드"],
        index=2,
        horizontal=True,
        key="sidebar_nav_dashboard",
    )
    if nav == "파일 처리":
        st.switch_page("app.py")
    elif nav == "수급자 관리":
        st.switch_page("pages/customer_manage.py")
    
    st.header("🔍 필터 설정")
    
    # 기간 설정
    st.subheader("📅 기간 설정")
    today = date.today()
    year_start = date(today.year, 1, 1)
    
    date_range = st.date_input(
        "분석 기간",
        value=(year_start, today),
        min_value=date(2020, 1, 1),
        max_value=today,
        key="date_range"
    )
    
    # date_range가 튜플인지 확인
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = year_start, today

# --- 데이터 로드 ---
data = load_dashboard_data(start_date, end_date)
df_emp_eval = data["emp_eval"]
df_ai_eval = data["ai_eval"]
df_users = data["users"]
prev_month_count = data["prev_month_count"]

# --- 사이드바 필터 (데이터 로드 후) ---
with st.sidebar:
    st.divider()
    
    # 직원 필터
    st.subheader("👤 직원 필터")
    user_names = df_users['name'].tolist() if not df_users.empty else []
    selected_users = st.multiselect(
        "직원 선택",
        options=user_names,
        default=[],
        placeholder="전체 직원",
        key="selected_users"
    )
    
    # 카테고리 필터
    categories = get_unique_values(df_emp_eval, 'category')
    selected_categories = st.multiselect(
        "카테고리",
        options=categories,
        default=[],
        placeholder="전체 카테고리",
        key="selected_categories"
    )
    
    # 평가 유형 필터
    eval_types = get_unique_values(df_emp_eval, 'evaluation_type')
    selected_eval_types = st.multiselect(
        "평가 유형",
        options=eval_types,
        default=[],
        placeholder="전체 유형",
        key="selected_eval_types"
    )
    
    st.divider()
    
    # 직원 바로가기
    st.subheader("⚡ 직원 바로가기")
    if not df_users.empty:
        selected_quick_user = st.radio(
            "직원 선택",
            options=["전체"] + user_names,
            index=0,
            key="quick_user_select",
            label_visibility="collapsed"
        )
    else:
        selected_quick_user = "전체"
        st.info("재직 중인 직원이 없습니다.")

# --- 필터 적용 ---
def apply_filters(df: pd.DataFrame, user_col: str = 'target_user_name') -> pd.DataFrame:
    """필터 조건 적용"""
    filtered = df.copy()
    
    # 직원 바로가기 우선 적용
    if selected_quick_user != "전체" and user_col in filtered.columns:
        filtered = filtered[filtered[user_col] == selected_quick_user]
    # 직원 멀티셀렉트 적용
    elif selected_users and user_col in filtered.columns:
        filtered = filtered[filtered[user_col].isin(selected_users)]
    
    # 카테고리 필터
    if selected_categories and 'category' in filtered.columns:
        filtered = filtered[filtered['category'].isin(selected_categories)]
    
    # 평가 유형 필터
    if selected_eval_types and 'evaluation_type' in filtered.columns:
        filtered = filtered[filtered['evaluation_type'].isin(selected_eval_types)]
    
    return filtered


# 필터 적용
df_emp_filtered = apply_filters(df_emp_eval)
df_ai_filtered = df_ai_eval.copy()  # AI 평가는 직원 필터 없음

# --- 메인 대시보드 ---
st.title("직원 관리 현황")
st.caption(f"분석 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")

# ============================================
# Section 1: 핵심 지표 (KPI Metrics)
# ============================================
st.markdown("---")
st.subheader("📈 핵심 지표")

col1, col2, col3, col4 = st.columns(4)

# 1. 총 지적 횟수
total_issues = len(df_emp_filtered)
with col1:
    st.metric(
        label="총 지적 횟수",
        value=f"{total_issues:,}건"
    )

# 2. 전월 대비 증감
current_month_count = len(df_emp_filtered[
    pd.to_datetime(df_emp_filtered['evaluation_date']).dt.month == today.month
]) if not df_emp_filtered.empty else 0
delta = current_month_count - prev_month_count
delta_str = f"+{delta}" if delta > 0 else str(delta)

with col2:
    st.metric(
        label="전월 대비 증감",
        value=f"{current_month_count:,}건",
        delta=f"{delta_str}건" if prev_month_count > 0 else "N/A"
    )

# 3. 평균 평가 점수
avg_score = df_emp_filtered['score'].mean() if not df_emp_filtered.empty and 'score' in df_emp_filtered.columns else 0
with col3:
    st.metric(
        label="평균 평가 점수",
        value=f"{avg_score:.2f}" if avg_score else "N/A"
    )

# 4. AI 품질 우수율
if not df_ai_filtered.empty and 'grade_code' in df_ai_filtered.columns:
    excellent_count = len(df_ai_filtered[df_ai_filtered['grade_code'] == '우수'])
    total_ai = len(df_ai_filtered)
    excellent_rate = (excellent_count / total_ai * 100) if total_ai > 0 else 0
else:
    excellent_rate = 0

with col4:
    st.metric(
        label="AI 품질 우수율",
        value=f"{excellent_rate:.1f}%"
    )

# ============================================
# Section 2: 트렌드 분석 (Charts)
# ============================================
st.markdown("---")
st.subheader("평가 분석")

if not df_emp_filtered.empty:
    # 날짜별, 평가유형별 집계
    df_trend = df_emp_filtered.copy()
    df_trend['evaluation_date'] = pd.to_datetime(df_trend['evaluation_date'])
    
    trend_data = df_trend.groupby(
        [df_trend['evaluation_date'].dt.date, 'evaluation_type']
    ).size().reset_index(name='count')
    trend_data.columns = ['date', 'evaluation_type', 'count']
    trend_data['date'] = pd.to_datetime(trend_data['date'])
    
    # Altair 라인 차트
    line_chart = alt.Chart(trend_data).mark_line(point=True).encode(
        x=alt.X('date:T', title='날짜', axis=alt.Axis(format='%Y-%m-%d')),
        y=alt.Y('count:Q', title='횟수'),
        color=alt.Color('evaluation_type:N', title='평가 유형', 
                       scale=alt.Scale(scheme='category10')),
        tooltip=[
            alt.Tooltip('date:T', title='날짜', format='%Y-%m-%d'),
            alt.Tooltip('evaluation_type:N', title='유형'),
            alt.Tooltip('count:Q', title='횟수')
        ]
    ).properties(
        height=350
    ).interactive()
    
    st.altair_chart(line_chart, use_container_width=True)
else:
    st.info("선택한 기간에 해당하는 직원 평가 데이터가 없습니다.")

# ============================================
# Section 3: AI 및 카테고리 분석 (Charts)
# ============================================
st.markdown("---")
st.subheader("🤖 AI 및 카테고리 분석")

chart_col1, chart_col2 = st.columns(2)

# Left: AI 평가 등급 분포 (Donut Chart)
with chart_col1:
    st.markdown("##### AI 평가 등급 분포")
    
    if not df_ai_filtered.empty and 'grade_code' in df_ai_filtered.columns:
        grade_counts = df_ai_filtered['grade_code'].value_counts().reset_index()
        grade_counts.columns = ['grade', 'count']
        
        # 등급 순서 정의
        grade_order = ['우수', '평균', '개선', '불량']
        grade_counts['grade'] = pd.Categorical(
            grade_counts['grade'], 
            categories=grade_order, 
            ordered=True
        )
        grade_counts = grade_counts.sort_values('grade')
        
        # 색상 매핑
        color_scale = alt.Scale(
            domain=['우수', '평균', '개선', '불량'],
            range=['#28a745', '#17a2b8', '#ffc107', '#dc3545']
        )
        
        donut_chart = alt.Chart(grade_counts).mark_arc(innerRadius=50).encode(
            theta=alt.Theta('count:Q'),
            color=alt.Color('grade:N', title='등급', scale=color_scale),
            tooltip=[
                alt.Tooltip('grade:N', title='등급'),
                alt.Tooltip('count:Q', title='건수')
            ]
        ).properties(
            height=300
        )
        
        st.altair_chart(donut_chart, use_container_width=True)
    else:
        st.info("AI 평가 데이터가 없습니다.")

# Right: 카테고리별 지적 횟수 (Bar Chart)
with chart_col2:
    st.markdown("##### 카테고리별 지적 횟수")
    
    if not df_emp_filtered.empty and 'category' in df_emp_filtered.columns:
        category_counts = df_emp_filtered['category'].value_counts().reset_index()
        category_counts.columns = ['category', 'count']
        
        bar_chart = alt.Chart(category_counts).mark_bar().encode(
            x=alt.X('category:N', title='카테고리', sort='-y'),
            y=alt.Y('count:Q', title='횟수'),
            color=alt.Color('category:N', legend=None, scale=alt.Scale(scheme='blues')),
            tooltip=[
                alt.Tooltip('category:N', title='카테고리'),
                alt.Tooltip('count:Q', title='횟수')
            ]
        ).properties(
            height=300
        )
        
        st.altair_chart(bar_chart, use_container_width=True)
    else:
        st.info("직원 평가 데이터가 없습니다.")

# ============================================
# Section 4: 직원별 상세 현황 (Dataframe)
# ============================================
st.markdown("---")
st.subheader("👥 직원별 상세 현황")

if not df_emp_filtered.empty:
    # 직원별 집계
    employee_summary = df_emp_filtered.groupby('target_user_name').agg(
        총_지적_횟수=('emp_eval_id', 'count'),
        평균_점수=('score', 'mean'),
        최근_코멘트=('comment', 'last')
    ).reset_index()
    
    # 주요 유형 (최빈값) 계산
    mode_types = df_emp_filtered.groupby('target_user_name')['evaluation_type'].agg(
        lambda x: x.mode().iloc[0] if not x.mode().empty else 'N/A'
    ).reset_index()
    mode_types.columns = ['target_user_name', '주요_유형']
    
    employee_summary = employee_summary.merge(mode_types, on='target_user_name', how='left')
    employee_summary.columns = ['직원명', '총 지적 횟수', '평균 점수', '최근 코멘트', '주요 유형']
    employee_summary = employee_summary[['직원명', '총 지적 횟수', '주요 유형', '평균 점수', '최근 코멘트']]
    
    # 평균 점수 포맷팅
    employee_summary['평균 점수'] = employee_summary['평균 점수'].round(2)
    
    # 최근 코멘트 길이 제한
    employee_summary['최근 코멘트'] = employee_summary['최근 코멘트'].apply(
        lambda x: (x[:50] + '...') if isinstance(x, str) and len(x) > 50 else x
    )
    
    # 정렬
    employee_summary = employee_summary.sort_values('총 지적 횟수', ascending=False)
    
    # 데이터프레임 표시 (컬럼 설정)
    st.dataframe(
        employee_summary,
        column_config={
            "직원명": st.column_config.TextColumn("직원명", width="medium"),
            "총 지적 횟수": st.column_config.ProgressColumn(
                "총 지적 횟수",
                format="%d건",
                min_value=0,
                max_value=int(employee_summary['총 지적 횟수'].max()) if not employee_summary.empty else 10,
            ),
            "주요 유형": st.column_config.TextColumn("주요 유형", width="medium"),
            "평균 점수": st.column_config.NumberColumn("평균 점수", format="%.2f"),
            "최근 코멘트": st.column_config.TextColumn("최근 코멘트", width="large"),
        },
        hide_index=True,
        use_container_width=True
    )
else:
    st.info("선택한 조건에 해당하는 데이터가 없습니다.")

# --- 푸터 ---
st.markdown("---")
st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
