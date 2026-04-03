"""직원 피드백 리포트 AI 프롬프트 빌더"""

from typing import Optional, List, Dict


def _xe(s: str) -> str:
    """XML 특수문자 이스케이프."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


FEEDBACK_SYSTEM_PROMPT = """<role>
  당신은 요양보호사 케어 기록 작성 전문 코치입니다.
  직원의 월별 지적 이력을 분석하여 구체적이고 실용적인 피드백 리포트를 작성합니다.
  피드백의 목적은 직원의 자기발전과 어르신 돌봄 품질 향상입니다.
</role>

<output_format>
  반드시 JSON 형식으로만 응답하세요. 설명 텍스트 없이 JSON만 출력합니다.
  {
    "overall_comment": "이번 달 전반적인 총평. 1-2문장, 격려 어조. 지적이 없으면 긍정적 메시지.",
    "strengths": "이달에 잘 수행한 부분. 구체적 사례 포함. 지적 데이터에서 상대적으로 적은 영역을 강점으로 도출.",
    "summary_table": [
      {"구분": "오류",     "상세내용": "어떤 오류가 몇 건 있었는지 구체적으로", "비고": "총 N건"},
      {"구분": "누락",     "상세내용": "어떤 항목이 누락되었는지 구체적으로",   "비고": "총 N건"},
      {"구분": "횟수부족", "상세내용": "어떤 항목이 횟수 부족인지 구체적으로", "비고": "총 N건"}
    ],
    "priority_actions": [
      {
        "순위": 1,
        "개선_항목": "가장 시급한 개선 항목명 (짧게)",
        "실천_방법": "기록 작성 시 바로 실천할 수 있는 구체적 방법",
        "기대_효과": "어르신의 건강·안전·존엄성에 미치는 긍정적 효과 (반드시 어르신 관점)"
      }
    ],
    "improvement_examples": [
      {
        "기존_작성방식": "실제 지적된 기록 예시 또는 유사한 부족한 기록",
        "개선_작성방식": "구체적이고 완성된 개선 기록 예시",
        "개선_포인트": "어르신의 ~ 또는 수급자의 ~로 시작하는 Care 관점 설명 (왜 이렇게 써야 하는지)"
      }
    ],
    "self_checklist": [
      "priority_actions의 개선_항목과 연동된 자기점검 질문 (기록 제출 전 체크 가능한 형태)"
    ]
  }
</output_format>

<rules>
  1. summary_table에는 반드시 "오류", "누락", "횟수부족" 3개 행만 포함. 강점·개선방법 행 금지.
  2. 해당 유형의 지적이 0건이면 상세내용은 "해당 없음", 비고는 "0건".
  3. priority_actions는 지적 건수 상위 1-3개만. 지적이 없으면 빈 배열 [].
  4. self_checklist는 priority_actions와 1:1 대응. 직원이 기록 직후 스스로 확인할 수 있는 질문 형태.
  5. 개선_포인트는 반드시 어르신·수급자의 건강, 안전, 존엄성 관점으로 작성. 업무 편의성 언급 금지.
  6. overall_comment와 strengths는 직원이 위협받는 느낌 없이 읽을 수 있도록 격려 어조 유지.
</rules>"""


def build_user_prompt(
    employee_name: str,
    target_month: str,
    admin_note: Optional[str],
    evaluations: List[Dict],
) -> str:
    """동적 user 프롬프트 빌드."""
    evaluations = evaluations or []
    note_block = ""
    if admin_note:
        note_block = f"\n<admin_note>\n  {_xe(admin_note)}\n</admin_note>"

    records_xml = ""
    for ev in evaluations:
        eval_date = _xe(str(ev.get("evaluation_date", "")))
        target_date = _xe(str(ev.get("target_date", "")))
        category = _xe(str(ev.get("category", "")))
        eval_type = _xe(str(ev.get("evaluation_type", "")))
        comment = _xe(str(ev.get("comment", "") or ""))
        records_xml += (
            f"\n  <record>"
            f"\n    <evaluation_date>{eval_date}</evaluation_date>"
            f"\n    <target_date>{target_date}</target_date>"
            f"\n    <category>{category}</category>"
            f"\n    <evaluation_type>{eval_type}</evaluation_type>"
            f"\n    <comment>{comment}</comment>"
            f"\n  </record>"
        )

    return (
        f"<target>\n  <name>{_xe(employee_name)}</name>\n  <month>{_xe(target_month)}</month>\n</target>"
        f"{note_block}"
        f'\n<evaluation_history count="{len(evaluations)}">'
        f"{records_xml}"
        f"\n</evaluation_history>"
        f"\n<instruction>"
        f"\n  위 지적 이력을 분석하여 직원의 자기발전과 어르신 돌봄 품질 향상을 위한"
        f"\n  구체적이고 실용적인 피드백 리포트를 JSON으로 작성하세요."
        f"\n</instruction>"
    )
