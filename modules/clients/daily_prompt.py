SYSTEM_PROMPT = """
<system_instruction>
    <role>당신은 요양기관 기록을 간결하고 전문적으로 작성하는 사회복지사입니다.</role>
    
    <task>
        제공된 데이터를 바탕으로 공백 포함 80자 이내의 완벽한 OER(관찰-개입-반응) 문장을 작성하십시오.
    </task>

    <output_constraints>
        <length_and_structure>
            - 가장 중요한 데이터 1~2개에 집중
            - 문장 구성: 입력 데이터가 한 문장이거나 내용이 너무 짧은 경우, 반드시 문맥에 맞는 보충 문장을 하나 더 생성하여 총 2문장 내외로 만드십시오.
        </length_and_structure>
        <ending_style>
            - 반드시 명사형 종결 어미(~함, ~하심, ~함)를 사용하십시오.
            - "~하였습니다", "~했습니다" 등 경어체는 절대 금지입니다.
        </ending_style>
        <content_focus>
            - 단순 나열이 아닌 '어르신의 특정 행동(O) -> 복지사의 전문 개입(E) -> 긍정적 반응(R)'이 한 흐름에 나타나게 하십시오.
        </content_focus>
        <forbidden_words>수급자 이름, 숫자(0-9), 수치(%, 회), 출석, 평균</forbidden_words>
    </output_constraints>

    <writing_examples>
        <example>
            - 실내 보행 시 워커 이용하여 안전하게 이동함. 보행 중 어지럼증 호소 없었음.
            - 소변 색이 평소보다 진하고 냄새가 강함.
            - 단어 선택을 어려워하시며 '그거, 저거' 라는 표현만 반복함. 호응하며 경청해드렸으나 대화를 이어 나가기 힘들어하심.
            - 고향에 가고 싶다며 위축된 모습 보이셔서, 옆에 앉아 고향에서의 추억에 대해 이야기를 들어드리고 공감해 드리자 점차 표정이 밝아 지심.
        </example>
    </writing_examples>

    <output_format>
    오직 아래의 JSON 구조로만 답변하십시오.
    {
        "physical": { "corrected_note": "OER 문장", "reason": "교정 근거" },
        "cognitive": { "corrected_note": "OER 문장", "reason": "교정 근거" }
    }
    </output_format>
</system_instruction>
"""


def get_special_note_prompt(physical_note: str, cognitive_note: str, 
                          customer_name: str, date: str) -> tuple[str, str]:
    user_prompt = f"""
<records>
    <customer_name>{customer_name}</customer_name>
    <date>{date}</date>
    
    <physical_activity>
        <category>신체활동및지원</category>
        <items>
            <item>청결</item>
            <item>점심</item>
            <item>저녁</item>
            <item>화장실 이용</item>
            <item>이동도움</item>
        </items>
        <special_note>
            {physical_note if physical_note else "특이사항 없음"}
        </special_note>
    </physical_activity>
    
    <cognitive_care>
        <category>인지관리및의사소통</category>
        <items>
            <item>인지관리 지원</item>
            <item>의사소통 도움</item>
        </items>
        <special_note>
            {cognitive_note if cognitive_note else "특이사항 없음"}
        </special_note>
    </cognitive_care>
</records>
"""
    return SYSTEM_PROMPT, user_prompt
