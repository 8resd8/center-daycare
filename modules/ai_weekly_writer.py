# modules/ai_weekly_writer.py

import json
import openai
import streamlit as st
from prompts import WEEKLY_WRITER_SYSTEM_PROMPT, WEEKLY_WRITER_USER_TEMPLATE

def generate_weekly_report(customer_name, date_range, analysis_result):
    # 1. AI에게 보낼 데이터 포맷팅
    input_content = _format_input_data(customer_name, date_range, analysis_result)

    # 2. OpenAI API 호출
    try:
        # Streamlit Secrets에서 API Key 가져오기


        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": WEEKLY_WRITER_SYSTEM_PROMPT},
                {"role": "user", "content": input_content}
            ],
            response_format={"type": "json_object"}, # JSON 강제 출력
            temperature=0.7 # 창의성 조절 (보고서는 약간 보수적으로)
        )

        # 3. 결과 파싱
        content = response.choices[0].message.content
        return json.loads(content)

    except Exception as e:
        return {"error": f"AI 생성 중 오류 발생: {str(e)}"}

def _format_input_data(name, date_range, data):
    """
    weekly_analysis.py의 복잡한 결과를 프롬프트에 넣기 좋게 문자열로 변환합니다.
    """
    header = data.get("header", {})
    notes = data.get("notes", {})

    # 1. 정량 지표 추출
    meal_h = header.get("meal_amount", {})
    toilet_h = header.get("toilet", {})
    type_h = header.get("meal_type", {})

    meal_trend = meal_h.get("trend", "변화없음")
    meal_prev = f"{meal_h.get('values', (0,0))[0]:.0f}%"
    meal_curr = f"{meal_h.get('values', (0,0))[1]:.0f}%"

    toilet_trend = toilet_h.get("trend", "변화없음")
    toilet_prev = f"{toilet_h.get('values', (0,0))[0]:.1f}회"
    toilet_curr = f"{toilet_h.get('values', (0,0))[1]:.1f}회"

    # 2. 중요 키워드 필터링 (통증, 거부 등)
    # daily_logs에서 '통증', '열', '거부' 등이 포함된 줄만 따로 뽑아 강조
    raw_logs = notes.get("this", [])
    health_issues = []
    behavior_issues = []

    for log in raw_logs:
        if any(k in log for k in ["통증", "열", "병원", "아프", "혈압"]):
            health_issues.append(log)
        if any(k in log for k in ["거부", "배회", "욕설", "싸움", "낙상"]):
            behavior_issues.append(log)

    # 3. 템플릿 완성
    return WEEKLY_WRITER_USER_TEMPLATE.format(
        name=name,
        start_date=date_range[0].strftime("%Y-%m-%d"),
        end_date=date_range[1].strftime("%Y-%m-%d"),

        meal_trend=meal_trend,
        meal_val_prev=meal_prev,
        meal_val_curr=meal_curr,

        toilet_trend=toilet_trend,
        toilet_val_prev=toilet_prev,
        toilet_val_curr=toilet_curr,

        diet_change=type_h.get("change", "-"),

        health_issues="\n".join(health_issues) if health_issues else "특이사항 없음",
        behavior_issues="\n".join(behavior_issues) if behavior_issues else "특이사항 없음",

        daily_logs="\n".join(raw_logs) # 전체 로그도 맥락 파악용으로 제공
    )