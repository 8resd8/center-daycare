"""weekly_data_analyzer 순수 함수 테스트

DB 의존성 없이 순수 Python 로직만 테스트합니다.
향후 백엔드 분리 시 분석 엔진으로 독립 배포 가능합니다.
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import modules.weekly_data_analyzer as analyzer


class TestScoreText:
    """_score_text 함수 테스트"""

    def test_empty_string_returns_50(self):
        """빈 문자열 → 기본 점수 50"""
        assert analyzer._score_text('') == 50

    def test_none_returns_50(self):
        """None → 기본 점수 50"""
        assert analyzer._score_text(None) == 50

    def test_positive_keyword_increases_score(self):
        """긍정 키워드('안정')가 있으면 점수 증가"""
        result = analyzer._score_text('상태 안정적임')
        assert result > 50

    def test_multiple_positive_keywords(self):
        """긍정 키워드 여러 개 → 더 높은 점수"""
        single = analyzer._score_text('안정')
        multiple = analyzer._score_text('안정 양호 호전')
        assert multiple >= single

    def test_negative_keyword_decreases_score(self):
        """부정 키워드('악화')가 있으면 점수 감소"""
        result = analyzer._score_text('상태 악화 경향')
        assert result < 50

    def test_score_bounded_above_zero(self):
        """점수는 0 이상이다 (모든 부정 키워드 포함 텍스트 사용)"""
        # NEGATIVE_KEYWORDS 전체를 포함한 텍스트 (max -45점 = 최솟값 5)
        text = ' '.join(analyzer.NEGATIVE_KEYWORDS)
        result = analyzer._score_text(text)
        assert result >= 0

    def test_score_bounded_below_100(self):
        """점수는 100 이하이다 (모든 긍정 키워드 포함 텍스트 사용)"""
        # POSITIVE_KEYWORDS 전체를 포함한 텍스트 (max +35점 = 최댓값 85)
        text = ' '.join(analyzer.POSITIVE_KEYWORDS)
        result = analyzer._score_text(text)
        assert result <= 100

    def test_mixed_keywords(self):
        """긍정/부정 키워드 혼재"""
        result = analyzer._score_text('안정적이나 통증 호소')
        assert 0 <= result <= 100

    @pytest.mark.parametrize("text,expected_direction", [
        ('개선됨', 'up'),
        ('안정적임', 'up'),
        ('호전 추세', 'up'),
        ('유지 중', 'up'),
        ('악화됨', 'down'),
        ('저하 경향', 'down'),
        ('통증 호소', 'down'),
    ])
    def test_keyword_direction(self, text, expected_direction):
        """키워드별 점수 방향 확인"""
        result = analyzer._score_text(text)
        if expected_direction == 'up':
            assert result >= 50
        else:
            assert result <= 50


class TestDetectMealType:
    """_detect_meal_type 함수 테스트"""

    def test_normal_meal(self):
        """일반식 감지"""
        assert analyzer._detect_meal_type('일반식 전량 섭취') == '일반식'

    def test_soft_meal(self):
        """죽식 감지"""
        assert analyzer._detect_meal_type('죽식 제공') == '죽식'

    def test_minced_meal(self):
        """다짐식 감지"""
        assert analyzer._detect_meal_type('다짐식 제공') == '다짐식'

    def test_tube_feeding(self):
        """경관식 감지"""
        assert analyzer._detect_meal_type('경관식 투여') == '경관식'

    def test_soft_food(self):
        """연식 감지"""
        assert analyzer._detect_meal_type('연식 제공') == '연식'

    def test_special_meal(self):
        """특식 감지"""
        assert analyzer._detect_meal_type('특식 제공') == '특식'

    def test_none_input(self):
        """None 입력 → None"""
        assert analyzer._detect_meal_type(None) is None

    def test_empty_string(self):
        """빈 문자열 → None"""
        assert analyzer._detect_meal_type('') is None

    def test_no_meal_type(self):
        """식사 유형 없음 → None"""
        assert analyzer._detect_meal_type('특이사항 없음') is None

    def test_returns_first_match(self):
        """첫 번째 일치 유형 반환"""
        result = analyzer._detect_meal_type('일반식 및 죽식 혼합')
        assert result in analyzer.MEAL_TYPES


class TestScoreMealAmount:
    """_score_meal_amount 함수 테스트"""

    def test_full_amount_keywords(self):
        """전량/정량/완 → 1.0"""
        assert analyzer._score_meal_amount('전량 섭취') == 1.0
        assert analyzer._score_meal_amount('정량 섭취') == 1.0
        assert analyzer._score_meal_amount('완식') == 1.0

    def test_half_amount_keywords(self):
        """절반/1/2/반 → 0.5"""
        assert analyzer._score_meal_amount('절반 섭취') == 0.5
        assert analyzer._score_meal_amount('1/2 이하') == 0.5

    def test_refusal_keywords(self):
        """거부/못/불가 → 0.0"""
        assert analyzer._score_meal_amount('거부') == 0.0
        assert analyzer._score_meal_amount('못 먹음') == 0.0

    def test_none_input_default(self):
        """None 입력 → 기본값 0.75"""
        assert analyzer._score_meal_amount(None) == 0.75

    def test_empty_string_default(self):
        """빈 문자열 → 기본값 0.75"""
        assert analyzer._score_meal_amount('') == 0.75

    def test_unknown_text_default(self):
        """알 수 없는 텍스트 → 기본값 0.75"""
        assert analyzer._score_meal_amount('특이사항 없음') == 0.75


class TestMealAmountLabel:
    """_meal_amount_label 함수 테스트"""

    def test_full_returns_label(self):
        """전량 → '전량' 레이블"""
        result = analyzer._meal_amount_label('전량 섭취')
        assert result == '전량'

    def test_half_returns_label(self):
        """절반 → '1/2이하' 레이블"""
        result = analyzer._meal_amount_label('절반 섭취')
        assert result == '1/2이하'

    def test_refusal_returns_label(self):
        """거부 → '거부' 레이블"""
        result = analyzer._meal_amount_label('거부함')
        assert result == '거부'

    def test_none_returns_no_info(self):
        """None → '정보없음'"""
        result = analyzer._meal_amount_label(None)
        assert result == '정보없음'

    def test_empty_returns_no_info(self):
        """빈 문자열 → '정보없음'"""
        result = analyzer._meal_amount_label('')
        assert result == '정보없음'

    def test_unknown_returns_no_info(self):
        """알 수 없는 텍스트 → '정보없음'"""
        result = analyzer._meal_amount_label('보통으로 드심')
        assert result == '정보없음'


class TestExtractToiletCount:
    """_extract_toilet_count 함수 테스트"""

    def test_single_count(self):
        """'소변 3회' → 3.0"""
        assert analyzer._extract_toilet_count('소변 3회') == 3.0

    def test_multiple_counts(self):
        """'소변 3회 대변 1회' → 4.0"""
        assert analyzer._extract_toilet_count('소변 3회 대변 1회') == 4.0

    def test_digit_only(self):
        """숫자만 있는 경우"""
        assert analyzer._extract_toilet_count('5') == 5.0

    def test_none_input(self):
        """None → None"""
        assert analyzer._extract_toilet_count(None) is None

    def test_empty_string(self):
        """빈 문자열 → None"""
        assert analyzer._extract_toilet_count('') is None

    def test_no_numbers(self):
        """숫자 없음 → None"""
        assert analyzer._extract_toilet_count('정상') is None

    def test_large_numbers(self):
        """큰 숫자도 처리 가능"""
        result = analyzer._extract_toilet_count('소변 10회 대변 5회')
        assert result == 15.0


class TestParseToiletBreakdown:
    """_parse_toilet_breakdown 함수 테스트"""

    def test_all_types(self):
        """대변/소변/기저귀 모두 포함"""
        result = analyzer._parse_toilet_breakdown('대변 2회 소변 4회 기저귀 1회')
        assert result['stool'] == 2.0
        assert result['urine'] == 4.0
        assert result['diaper'] == 1.0

    def test_stool_only(self):
        """대변만 있는 경우"""
        result = analyzer._parse_toilet_breakdown('대변 2회')
        assert result['stool'] == 2.0
        assert result['urine'] == 0.0
        assert result['diaper'] == 0.0

    def test_urine_only(self):
        """소변만 있는 경우"""
        result = analyzer._parse_toilet_breakdown('소변 5회')
        assert result['urine'] == 5.0
        assert result['stool'] == 0.0

    def test_none_input(self):
        """None → 빈 딕셔너리"""
        result = analyzer._parse_toilet_breakdown(None)
        assert result == {}

    def test_empty_string(self):
        """빈 문자열 → 모두 0"""
        result = analyzer._parse_toilet_breakdown('')
        assert result == {}

    def test_alternative_keywords_stool(self):
        """'배변'도 대변으로 인식"""
        result = analyzer._parse_toilet_breakdown('배변 3회')
        assert result['stool'] == 3.0

    def test_alternative_keywords_urine(self):
        """'배뇨'도 소변으로 인식"""
        result = analyzer._parse_toilet_breakdown('배뇨 4회')
        assert result['urine'] == 4.0

    def test_alternative_keywords_diaper(self):
        """'교환'도 기저귀로 인식"""
        result = analyzer._parse_toilet_breakdown('교환 2회')
        assert result['diaper'] == 2.0

    def test_multiple_entries_summed(self):
        """같은 유형 여러 번 언급 시 합산"""
        result = analyzer._parse_toilet_breakdown('소변 3회 배뇨 2회')
        assert result['urine'] == 5.0


class TestOptimizeDataframe:
    """_optimize_dataframe 함수 테스트"""

    def test_empty_dataframe_returns_unchanged(self):
        """빈 DataFrame은 그대로 반환"""
        import pandas as pd
        df = pd.DataFrame()
        result = analyzer._optimize_dataframe(df)
        assert result.empty

    def test_category_conversion_for_low_cardinality(self):
        """중복이 많은 컬럼이 category 타입으로 변환된다"""
        import pandas as pd
        data = {'meal_type': ['일반식'] * 10 + ['죽식'] * 5}
        df = pd.DataFrame(data)
        result = analyzer._optimize_dataframe(df)
        assert result['meal_type'].dtype.name == 'category'

    def test_high_cardinality_column_not_converted(self):
        """중복이 적은 컬럼은 변환되지 않는다"""
        import pandas as pd
        # 모든 값이 고유한 경우
        data = {'meal_type': [f'type_{i}' for i in range(20)]}
        df = pd.DataFrame(data)
        result = analyzer._optimize_dataframe(df)
        # unique 값 비율이 50% 초과이면 category 변환 안 함
        assert result['meal_type'].dtype.name != 'category'


class TestComputeWeeklyStatus:
    """compute_weekly_status 함수 테스트 (DB mock 사용)"""

    def test_invalid_date_format_returns_error(self):
        """날짜 형식이 잘못되면 error 반환"""
        result = analyzer.compute_weekly_status(
            customer_name='홍길동',
            week_start_str='invalid-date',
            customer_id=1
        )
        assert 'error' in result

    def test_no_rows_returns_empty_data(self):
        """레코드가 없을 때 빈 데이터 반환"""
        with patch('modules.weekly_data_analyzer._fetch_two_week_records',
                   return_value=([], (date(2024, 1, 1), date(2024, 1, 7)),
                                 (date(2024, 1, 8), date(2024, 1, 14)))):
            with patch('modules.weekly_data_analyzer._load_cached_weekly_status',
                       return_value=None):
                result = analyzer.compute_weekly_status(
                    customer_name='홍길동',
                    week_start_str='2024-01-08',
                    customer_id=1
                )

        assert result.get('data') == [] or 'scores' in result

    def test_valid_date_format_processes(self):
        """유효한 날짜 형식으로 정상 처리"""
        sample_rows = [
            {
                'date': date(2024, 1, 8),
                'physical_note': '정상',
                'cognitive_note': '양호',
                'nursing_note': None,
                'functional_note': None,
            }
        ]
        prev_range = (date(2024, 1, 1), date(2024, 1, 7))
        curr_range = (date(2024, 1, 8), date(2024, 1, 14))

        with patch('modules.weekly_data_analyzer._fetch_two_week_records',
                   return_value=(sample_rows, prev_range, curr_range)):
            with patch('modules.weekly_data_analyzer._load_cached_weekly_status',
                       return_value=None):
                with patch('modules.weekly_data_analyzer._save_weekly_status_cache'):
                    with patch('modules.weekly_data_analyzer.analyze_weekly_trend',
                               return_value={}):
                        result = analyzer.compute_weekly_status(
                            customer_name='홍길동',
                            week_start_str='2024-01-08',
                            customer_id=1
                        )

        assert 'scores' in result
        assert 'ranges' in result

    def test_cached_result_returned_when_available(self):
        """캐시가 있으면 DB 조회 없이 캐시 반환"""
        cached = {
            'scores': {'physical': {'label': '신체활동', 'prev': 55.0, 'curr': 60.0}},
            'ranges': (
                (date(2024, 1, 1), date(2024, 1, 7)),
                (date(2024, 1, 8), date(2024, 1, 14))
            )
        }

        with patch('modules.weekly_data_analyzer._load_cached_weekly_status',
                   return_value=cached):
            with patch('modules.weekly_data_analyzer._fetch_two_week_records') as mock_fetch:
                result = analyzer.compute_weekly_status(
                    customer_name='홍길동',
                    week_start_str='2024-01-08',
                    customer_id=1,
                    use_cache=True
                )

        # 캐시가 있으면 fetch 호출 없음
        mock_fetch.assert_not_called()
        assert result == cached

    def test_no_cache_when_use_cache_false(self):
        """use_cache=False이면 캐시를 사용하지 않는다"""
        with patch('modules.weekly_data_analyzer._load_cached_weekly_status') as mock_cache:
            with patch('modules.weekly_data_analyzer._fetch_two_week_records',
                       return_value=([], (date(2024, 1, 1), date(2024, 1, 7)),
                                     (date(2024, 1, 8), date(2024, 1, 14)))):
                analyzer.compute_weekly_status(
                    customer_name='홍길동',
                    week_start_str='2024-01-08',
                    customer_id=1,
                    use_cache=False
                )

        mock_cache.assert_not_called()


class TestAnalyzeWeeklyTrend:
    """analyze_weekly_trend 함수 테스트 (순수 DataFrame 로직)"""

    @pytest.fixture
    def sample_rows(self):
        return [
            {
                'date': date(2024, 1, 8),
                'total_service_time': '9시간',
                'physical_note': '신체 양호',
                'cognitive_note': '인지 정상',
                'nursing_note': None,
                'functional_note': None,
                'meal_breakfast': '일반식 전량',
                'meal_lunch': '일반식 전량',
                'meal_dinner': None,
                'toilet_care': '소변 3회 대변 1회',
                'bath_time': '10:00',
                'bp_temp': '120/80 36.5',
                'prog_therapy': '완료',
                'prog_enhance_detail': '미니골프 활동 참여',
            },
            {
                'date': date(2024, 1, 9),
                'total_service_time': '9시간',
                'physical_note': '보행 보조',
                'cognitive_note': '대화 활발',
                'nursing_note': None,
                'functional_note': None,
                'meal_breakfast': '죽식 절반',
                'meal_lunch': '일반식 전량',
                'meal_dinner': None,
                'toilet_care': '소변 2회',
                'bath_time': None,
                'bp_temp': None,
                'prog_therapy': None,
                'prog_enhance_detail': None,
            }
        ]

    @pytest.fixture
    def date_ranges(self):
        prev_range = (date(2024, 1, 1), date(2024, 1, 7))
        curr_range = (date(2024, 1, 8), date(2024, 1, 14))
        return prev_range, curr_range

    def test_empty_rows_returns_empty_dict(self):
        """빈 레코드 → 빈 딕셔너리"""
        result = analyzer.analyze_weekly_trend(
            rows=[],
            prev_range=(date(2024, 1, 1), date(2024, 1, 7)),
            curr_range=(date(2024, 1, 8), date(2024, 1, 14)),
            customer_id=1
        )
        assert result == {}

    def test_result_has_required_keys(self, sample_rows, date_ranges):
        """결과 딕셔너리에 필수 키가 포함된다"""
        prev_range, curr_range = date_ranges

        with patch('modules.weekly_data_analyzer.WeeklyStatusRepository') as MockRepo:
            MockRepo.return_value.load_weekly_status.return_value = None
            result = analyzer.analyze_weekly_trend(
                rows=sample_rows,
                prev_range=prev_range,
                curr_range=curr_range,
                customer_id=1
            )

        required_keys = [
            'header', 'notes', 'weekly_table', 'category_notes', 'ai_payload',
            'prev_prog_entries', 'curr_prog_entries',
        ]
        for key in required_keys:
            assert key in result, f"'{key}' 키가 결과에 없음"

    def test_notes_has_last_and_this(self, sample_rows, date_ranges):
        """notes에 'last'와 'this' 키가 포함된다"""
        prev_range, curr_range = date_ranges

        with patch('modules.weekly_data_analyzer.WeeklyStatusRepository') as MockRepo:
            MockRepo.return_value.load_weekly_status.return_value = None
            result = analyzer.analyze_weekly_trend(
                rows=sample_rows,
                prev_range=prev_range,
                curr_range=curr_range,
                customer_id=1
            )

        assert 'last' in result['notes']
        assert 'this' in result['notes']

    def test_weekly_table_has_two_rows(self, sample_rows, date_ranges):
        """weekly_table에 저번주/이번주 두 행이 포함된다"""
        prev_range, curr_range = date_ranges

        with patch('modules.weekly_data_analyzer.WeeklyStatusRepository') as MockRepo:
            MockRepo.return_value.load_weekly_status.return_value = None
            result = analyzer.analyze_weekly_trend(
                rows=sample_rows,
                prev_range=prev_range,
                curr_range=curr_range,
                customer_id=1
            )

        assert len(result['weekly_table']) == 2
        weeks = [row['주간'] for row in result['weekly_table']]
        assert '저번주' in weeks
        assert '이번주' in weeks

    def test_attendance_counted_correctly(self, sample_rows, date_ranges):
        """출석일이 올바르게 계산된다"""
        prev_range, curr_range = date_ranges

        with patch('modules.weekly_data_analyzer.WeeklyStatusRepository') as MockRepo:
            MockRepo.return_value.load_weekly_status.return_value = None
            result = analyzer.analyze_weekly_trend(
                rows=sample_rows,
                prev_range=prev_range,
                curr_range=curr_range,
                customer_id=1
            )

        this_week_row = next(r for r in result['weekly_table'] if r['주간'] == '이번주')
        # 2024-01-08, 2024-01-09 두 날 모두 출석
        assert this_week_row['출석일'] == 2

    def test_absence_not_counted(self, date_ranges):
        """결석/미이용 날짜는 출석에 포함되지 않는다"""
        prev_range, curr_range = date_ranges
        rows_with_absence = [
            {
                'date': date(2024, 1, 8),
                'total_service_time': '결석',
                'physical_note': None,
                'cognitive_note': None,
                'nursing_note': None,
                'functional_note': None,
                'meal_breakfast': None,
                'meal_lunch': None,
                'meal_dinner': None,
                'toilet_care': None,
                'bath_time': None,
                'bp_temp': None,
                'prog_therapy': None,
                'prog_enhance_detail': None,
            }
        ]

        with patch('modules.weekly_data_analyzer.WeeklyStatusRepository') as MockRepo:
            MockRepo.return_value.load_weekly_status.return_value = None
            result = analyzer.analyze_weekly_trend(
                rows=rows_with_absence,
                prev_range=prev_range,
                curr_range=curr_range,
                customer_id=1
            )

        this_week_row = next(r for r in result['weekly_table'] if r['주간'] == '이번주')
        assert this_week_row['출석일'] == 0

    # ── prog_entries 관련 테스트 ────────────────────────────────────────

    def _make_row(self, row_date: date, prog_enhance_detail=None, **overrides):
        """테스트용 기본 row 생성 헬퍼"""
        row = {
            'date': row_date,
            'total_service_time': '9시간',
            'physical_note': None,
            'cognitive_note': None,
            'nursing_note': None,
            'functional_note': None,
            'meal_breakfast': None,
            'meal_lunch': None,
            'meal_dinner': None,
            'toilet_care': None,
            'bath_time': None,
            'bp_temp': None,
            'prog_therapy': None,
            'prog_enhance_detail': prog_enhance_detail,
        }
        row.update(overrides)
        return row

    def test_prog_enhance_있으면_curr_entries_포함(self, date_ranges):
        """prog_enhance_detail 있는 이번주 날짜 → curr_prog_entries에 포함"""
        prev_range, curr_range = date_ranges
        rows = [self._make_row(date(2024, 1, 8), prog_enhance_detail='미니골프 활동 참여')]

        with patch('modules.weekly_data_analyzer.WeeklyStatusRepository') as MockRepo:
            MockRepo.return_value.load_weekly_status.return_value = None
            result = analyzer.analyze_weekly_trend(
                rows=rows, prev_range=prev_range, curr_range=curr_range, customer_id=1
            )

        assert len(result['curr_prog_entries']) == 1
        assert result['curr_prog_entries'][0]['detail'] == '미니골프 활동 참여'

    def test_prog_enhance_날짜_MM_DD_형식(self, date_ranges):
        """entries의 date가 'MM-DD' 형식이어야 한다"""
        import re
        prev_range, curr_range = date_ranges
        rows = [self._make_row(date(2024, 1, 8), prog_enhance_detail='활동')]

        with patch('modules.weekly_data_analyzer.WeeklyStatusRepository') as MockRepo:
            MockRepo.return_value.load_weekly_status.return_value = None
            result = analyzer.analyze_weekly_trend(
                rows=rows, prev_range=prev_range, curr_range=curr_range, customer_id=1
            )

        entries = result['curr_prog_entries']
        assert len(entries) == 1
        assert re.fullmatch(r'\d{2}-\d{2}', entries[0]['date']), f"날짜 형식 오류: {entries[0]['date']}"
        assert entries[0]['date'] == '01-08'

    def test_prog_enhance_detail_내용_포함(self, sample_rows, date_ranges):
        """entries의 detail 값이 원본 텍스트와 일치해야 한다"""
        prev_range, curr_range = date_ranges

        with patch('modules.weekly_data_analyzer.WeeklyStatusRepository') as MockRepo:
            MockRepo.return_value.load_weekly_status.return_value = None
            result = analyzer.analyze_weekly_trend(
                rows=sample_rows, prev_range=prev_range, curr_range=curr_range, customer_id=1
            )

        # sample_rows의 첫 번째 row(01-08)에 '미니골프 활동 참여' 있음
        details = [e['detail'] for e in result['curr_prog_entries']]
        assert '미니골프 활동 참여' in details

    def test_prog_enhance_None_제외(self, date_ranges):
        """prog_enhance_detail=None → entries에 포함 안 됨"""
        prev_range, curr_range = date_ranges
        rows = [self._make_row(date(2024, 1, 8), prog_enhance_detail=None)]

        with patch('modules.weekly_data_analyzer.WeeklyStatusRepository') as MockRepo:
            MockRepo.return_value.load_weekly_status.return_value = None
            result = analyzer.analyze_weekly_trend(
                rows=rows, prev_range=prev_range, curr_range=curr_range, customer_id=1
            )

        assert result['curr_prog_entries'] == []

    def test_prog_enhance_공백만_있으면_제외(self, date_ranges):
        """공백만 있는 prog_enhance_detail → strip 후 empty → entries에 포함 안 됨"""
        prev_range, curr_range = date_ranges
        rows = [self._make_row(date(2024, 1, 8), prog_enhance_detail='   ')]

        with patch('modules.weekly_data_analyzer.WeeklyStatusRepository') as MockRepo:
            MockRepo.return_value.load_weekly_status.return_value = None
            result = analyzer.analyze_weekly_trend(
                rows=rows, prev_range=prev_range, curr_range=curr_range, customer_id=1
            )

        assert result['curr_prog_entries'] == []

    def test_prog_enhance_지난주_prev_entries_분리(self, date_ranges):
        """지난주 records → prev_prog_entries, 이번주 records → curr_prog_entries"""
        prev_range, curr_range = date_ranges
        # prev_range: (2024-01-01, 2024-01-07), curr_range: (2024-01-08, 2024-01-14)
        rows = [
            self._make_row(date(2024, 1, 3), prog_enhance_detail='지난주 활동'),
            self._make_row(date(2024, 1, 8), prog_enhance_detail='이번주 활동'),
        ]

        with patch('modules.weekly_data_analyzer.WeeklyStatusRepository') as MockRepo:
            MockRepo.return_value.load_weekly_status.return_value = None
            result = analyzer.analyze_weekly_trend(
                rows=rows, prev_range=prev_range, curr_range=curr_range, customer_id=1
            )

        assert len(result['prev_prog_entries']) == 1
        assert result['prev_prog_entries'][0]['detail'] == '지난주 활동'
        assert len(result['curr_prog_entries']) == 1
        assert result['curr_prog_entries'][0]['detail'] == '이번주 활동'

    def test_prog_enhance_필드_없어도_빈배열(self, date_ranges):
        """rows에 prog_enhance_detail 키 자체 없어도 빈 배열 반환 (KeyError 아님)"""
        prev_range, curr_range = date_ranges
        rows = [
            {
                'date': date(2024, 1, 8),
                'total_service_time': '9시간',
                'physical_note': '정상',
                'cognitive_note': '양호',
                'nursing_note': None,
                'functional_note': None,
                'meal_breakfast': None,
                'meal_lunch': None,
                'meal_dinner': None,
                'toilet_care': None,
                'bath_time': None,
                'bp_temp': None,
                'prog_therapy': None,
                # prog_enhance_detail 키 없음
            }
        ]

        with patch('modules.weekly_data_analyzer.WeeklyStatusRepository') as MockRepo:
            MockRepo.return_value.load_weekly_status.return_value = None
            result = analyzer.analyze_weekly_trend(
                rows=rows, prev_range=prev_range, curr_range=curr_range, customer_id=1
            )

        assert result['curr_prog_entries'] == []
        assert result['prev_prog_entries'] == []


class TestFetchTwoWeekRecords:
    """_fetch_two_week_records 필드 포함 검증"""

    def _make_db_record(self, record_date: date, **overrides):
        record = {
            'date': record_date,
            'total_service_time': '9시간',
            'physical_note': '정상',
            'cognitive_note': '양호',
            'nursing_note': None,
            'functional_note': None,
            'meal_breakfast': '일반식 전량',
            'meal_lunch': '일반식 전량',
            'meal_dinner': None,
            'toilet_care': '소변 3회',
            'bath_time': '10:00',
            'bp_temp': '120/80',
            'prog_therapy': '완료',
            'prog_enhance_detail': None,
        }
        record.update(overrides)
        return record

    def test_prog_enhance_detail_필드_포함(self):
        """반환 records에 prog_enhance_detail 키 포함 (누락 시 KeyError 위험)"""
        db_record = self._make_db_record(
            date(2024, 1, 8), prog_enhance_detail='미니골프 활동 참여'
        )

        with (
            patch('modules.repositories.CustomerRepository') as MockCR,
            patch('modules.weekly_data_analyzer.DailyInfoRepository') as MockDR,
        ):
            MockCR.return_value.find_by_name.return_value = {'customer_id': 1}
            MockDR.return_value.get_customer_records.return_value = [db_record]

            records, _, _ = analyzer._fetch_two_week_records('홍길동', date(2024, 1, 8))

        assert len(records) == 1
        assert 'prog_enhance_detail' in records[0], "prog_enhance_detail 필드가 변환된 record에 없음"
        assert records[0]['prog_enhance_detail'] == '미니골프 활동 참여'

    def test_prog_enhance_detail_없는_레코드_None으로_처리(self):
        """DB record에 prog_enhance_detail 키 없어도 None으로 처리 (KeyError 아님)"""
        db_record = {
            'date': date(2024, 1, 8),
            'total_service_time': '9시간',
            'physical_note': '정상',
            'cognitive_note': '양호',
            'nursing_note': None,
            'functional_note': None,
            # prog_enhance_detail 키 없음
        }

        with (
            patch('modules.repositories.CustomerRepository') as MockCR,
            patch('modules.weekly_data_analyzer.DailyInfoRepository') as MockDR,
        ):
            MockCR.return_value.find_by_name.return_value = {'customer_id': 1}
            MockDR.return_value.get_customer_records.return_value = [db_record]

            records, _, _ = analyzer._fetch_two_week_records('홍길동', date(2024, 1, 8))

        assert len(records) == 1
        assert 'prog_enhance_detail' in records[0]
        assert records[0]['prog_enhance_detail'] is None

    def test_수급자_없으면_빈_records(self):
        """find_by_name이 None 반환 시 빈 records 반환"""
        with patch('modules.repositories.CustomerRepository') as MockCR:
            MockCR.return_value.find_by_name.return_value = None
            records, prev_range, curr_range = analyzer._fetch_two_week_records(
                '없는사람', date(2024, 1, 8)
            )

        assert records == []
        assert prev_range is not None
        assert curr_range is not None
