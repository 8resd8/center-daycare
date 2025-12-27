import streamlit as st
from openai import OpenAI
import json
from daily_prompt import get_evaluation_prompt


def evaluate_note_with_ai(note_text: str, category: str = '', writer: str = '', customer_name: str = '', date: str = ''):
    if not note_text or note_text.strip() in ['특이사항 없음', '결석']:
        return None
    
    try:
        client = OpenAI(api_key=st.secrets['OPENAI_API_KEY'])
    except Exception as e:
        print(f'OpenAI 클라이언트 초기화 오류: {e}')
        return None
    
    system_prompt, user_prompt = get_evaluation_prompt(note_text, category, writer, customer_name, date)
    
    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            temperature=0.7,
            response_format={'type': 'json_object'}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f'AI 평가 중 오류 발생: {e}')
        return None


def save_ai_evaluation(record_id: int, category: str, note_writer_user_id: int, evaluation_result: dict, db_conn, original_text: str = None):
    cursor = db_conn.cursor()
    
    category_map = {
        "PHYSICAL": "신체",
        "COGNITIVE": "인지", 
        "NURSING": "간호",
        "RECOVERY": "기능"
    }
    korean_category = category_map.get(category, category)
    
    valid_grades = ['우수', '평균', '개선', '평가없음']
    
    if evaluation_result:
        content_quality_score = evaluation_result.get('consistency_score', 0)
        specificity_score = evaluation_result.get('specificity_score', 0)
        professionalism_score = evaluation_result.get('grammar_score', 0)
        
        average_score = (content_quality_score + specificity_score + professionalism_score) / 3

        if average_score >= 70:
            korean_grade = '우수'
        elif average_score >= 55:
            korean_grade = '평균'
        else:
            korean_grade = '개선'
        
        reason_text = evaluation_result.get('reasoning_process')
        suggestion_text = evaluation_result.get('suggestion_text')
    else:
        # For "특이사항 없음" or empty notes
        content_quality_score = 0
        specificity_score = 0
        professionalism_score = 0
        korean_grade = '평가없음'
        reason_text = ''
        suggestion_text = ''
    
    check_sql = 'SELECT ai_eval_id FROM ai_evaluations WHERE record_id = %s AND category = %s'
    cursor.execute(check_sql, (record_id, korean_category))
    
    if cursor.fetchone():
        update_sql = '''
            UPDATE ai_evaluations SET
                consistency_score = %s,
                grammar_score = %s,
                specificity_score = %s,
                grade_code = %s,
                reason_text = %s,
                suggestion_text = %s,
                original_text = %s,
                note_writer_user_id = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE record_id = %s AND category = %s
        '''
        cursor.execute(update_sql, (
            content_quality_score, professionalism_score, specificity_score,
            korean_grade, reason_text, suggestion_text, original_text,
            note_writer_user_id, record_id, korean_category
        ))
    else:
        insert_sql = '''
            INSERT INTO ai_evaluations (
                record_id, category, consistency_score, grammar_score,
                specificity_score, grade_code, reason_text,
                suggestion_text, original_text, note_writer_user_id, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
        '''
        cursor.execute(insert_sql, (
            record_id, korean_category, content_quality_score, professionalism_score,
            specificity_score, korean_grade, reason_text,
            suggestion_text, original_text, note_writer_user_id
        ))
    
    db_conn.commit()
    cursor.close()


def process_daily_note_evaluation(record_id: int, category: str, note_text: str, note_writer_user_id: int, writer: str = '', customer_name: str = '', date: str = '', db_conn=None):
    
    if not note_text or note_text.strip() in ['특이사항 없음', '결석', '']:
        evaluation_result = None
    else:
        evaluation_result = evaluate_note_with_ai(note_text, category, writer, customer_name, date)
    
    if evaluation_result:
        # Calculate grade on server based on scores
        consistency_score = evaluation_result.get('consistency_score', 0)
        grammar_score = evaluation_result.get('grammar_score', 0)
        specificity_score = evaluation_result.get('specificity_score', 0)
        
        average_score = (consistency_score + grammar_score + specificity_score) / 3
        
        if average_score >= 90:
            korean_grade = '우수'
        elif average_score >= 75:
            korean_grade = '평균'
        else:
            korean_grade = '개선'
        
        # Add the calculated grade to the evaluation result
        evaluation_result['grade_code'] = korean_grade
    else:
        korean_grade = '평가없음'
        # Create evaluation result with 0 scores for empty or special cases
        evaluation_result = {
            'consistency_score': 0,
            'grammar_score': 0,
            'specificity_score': 0,
            'grade_code': '평가없음',
            'reasoning_process': '',
            'suggestion_text': ''
        }
    
    save_ai_evaluation(record_id, category, note_writer_user_id, evaluation_result, db_conn, note_text)
    
    return {
        'grade_code': korean_grade,  # Return Korean grade
        'evaluation': evaluation_result
    }
