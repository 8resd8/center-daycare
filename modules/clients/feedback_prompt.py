"""직원 피드백 리포트 AI 프롬프트 빌더"""

from typing import Optional, List, Dict

FEEDBACK_SYSTEM_PROMPT = """<role>
  당신은 요양보호사 케어 기록 작성 전문 코치입니다.
  직원의 월별 지적 이력을 분석하여 구체적이고 실용적인 피드백 리포트를 작성합니다.
</role>

<output_format>
  반드시 JSON 형식으로만 응답하세요. 설명 텍스트 없이 JSON만 출력합니다.
  {
    "summary_table": [
      {"구분": "오류",               "상세내용": "...", "비고": "총 N건"},
      {"구분": "누락",               "상세내용": "...", "비고": "총 N건"},
      {"구분": "횟수부족",           "상세내용": "...", "비고": "총 N건"},
      {"구분": "좋았던 부분",        "상세내용": "...", "비고": ""},
      {"구분": "개선해야 하는 부분", "상세내용": "...", "비고": ""},
      {"구분": "개선방법",           "상세내용": "...", "비고": ""}
    ],
    "improvement_examples": [
      {"기존_작성방식": "...", "개선_작성방식": "..."}
    ]
  }
</output_format>"""


def build_user_prompt(
    employee_name: str,
    target_month: str,
    admin_note: Optional[str],
    evaluations: List[Dict],
) -> str:
    """동적 user 프롬프트 빌드."""
    note_block = ""
    if admin_note:
        note_block = f"\n<admin_note>\n  {admin_note}\n</admin_note>"

    records_xml = ""
    for ev in evaluations:
        eval_date = ev.get("evaluation_date", "")
        target_date = ev.get("target_date", "")
        category = ev.get("category", "")
        eval_type = ev.get("evaluation_type", "")
        comment = ev.get("comment", "") or ""
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
        f"<target>\n  <name>{employee_name}</name>\n  <month>{target_month}</month>\n</target>"
        f"{note_block}"
        f'\n<evaluation_history count="{len(evaluations)}">'
        f"{records_xml}"
        f"\n</evaluation_history>"
        f"\n<instruction>"
        f"\n  위 지적 이력을 분석하여 직원이 더 나은 케어 기록을 작성할 수 있도록"
        f"\n  구체적이고 실용적인 피드백 리포트를 JSON으로 작성하세요."
        f"\n</instruction>"
    )
