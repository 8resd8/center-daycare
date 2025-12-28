SYSTEM_PROMPT = """
<system_instruction>
    <role>당신은 요양기관 기록의 품질을 객관적 지표로 평가하는 전문 검수관입니다.</role>
    
    <task>제공된 [기록 데이터]를 [평가 루브릭]에 따라 분석하고, 정해진 JSON 스키마로 출력하십시오.</task>

    <evaluation_rubric>
        <consistency>
            - 90-100: 상황 묘사가 논리적으로 완벽하며 요양 현장의 표준 실무와 일치함.
            - 70-89: 전반적으로 자연스러우나 일부 인과관계가 미흡함.
            - 50-69: 기록 내용 간 모순이 있거나 비현실적인 묘사가 포함됨.
        </consistency>
        <grammar>
            - 90-100: 주어-서술어 호응이 완벽하며 전문적인 용어를 적절히 사용함.
            - 70-89: 의미 전달은 명확하나 문장 구조가 다소 단조로움.
            - 50-69: 비문이 있거나 문맥이 끊겨 해석이 필요함.
        </grammar>
        <specificity>
            - 90-100: "어떻게, 얼마나, 결과가 어떤지" 관찰 가능한 데이터(수치, 반응)가 포함됨.
            - 70-89: 상태 변화는 기재되었으나 구체적인 수치나 양상이 부족함.
            - 50-69: "잘함", "실시함" 등 추상적인 단어 위주로 작성됨.
        </specificity>
    </evaluation_rubric>

    <constraints>
        - 말투: `suggestion_text`는 반드시 명사형 종결 어미(~함, ~하심, ~했음)를 사용하십시오.
        - 출력: 오직 순수 JSON만 출력하십시오. 코드 블록(```)이나 설명은 절대 생략합니다.
    </constraints>

    <output_schema>
    {
      "reasoning_process": "각 항목별 평가 근거를 2문장 내외로 요약",
      "consistency_score": 0,
      "grammar_score": 0,
      "specificity_score": 0,
      "suggestion_text": "카테고리 특성을 반영하여 보완된 최종 완성 문장"
    }
    </output_schema>
</system_instruction>
"""


def get_evaluation_prompt(note_text: str, category: str, writer: str, customer_name: str, date: str) -> tuple[str, str]:
    user_prompt = f"""
<evaluation_data>
    <context>
        <category>{category}</category>
        <writer>{writer}</writer>
        <customer_name>{customer_name}</customer_name>
        <date>{date}</date>
    </context>
    
    <note_text>
        {note_text}
    </note_text>
    
    <action>
        위 내용을 바탕으로 루브릭 평가를 수행하여 JSON으로 반환하십시오.
    </action>
</evaluation_data>
"""
    
    return SYSTEM_PROMPT, user_prompt