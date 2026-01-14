"""공통으로 사용되는 열거형 정의"""

from enum import Enum


class CategoryType(Enum):
    """카테고리 타입 열거형"""
    BASIC_INFO = "기본정보"
    PHYSICAL_ACTIVITY = "신체활동지원"
    COGNITIVE_CARE = "인지관리"
    NURSING_CARE = "간호관리"
    FUNCTIONAL_RECOVERY = "기능회복"


class CategoryDisplay:
    """카테고리 표시명 상수"""
    KOREAN_NAMES = [
        CategoryType.BASIC_INFO.value,
        CategoryType.PHYSICAL_ACTIVITY.value,
        CategoryType.COGNITIVE_CARE.value,
        CategoryType.NURSING_CARE.value,
        CategoryType.FUNCTIONAL_RECOVERY.value
    ]
    
    # 주간상태변화평가에서 사용하는 아이콘 포함 이름
    WEEKLY_DISPLAY_NAMES = [
        "ℹ️ 기본 정보",
        "💪 신체활동지원",
        "🧠 인지관리",
        "🩺 간호관리",
        "🏃 기능회복"
    ]
    
    # 한글 카테고리명을 DB 영문명으로 변환
    KOREAN_TO_ENGLISH = {
        "기본정보": "공통",
        "신체활동지원": "신체",
        "인지관리": "인지",
        "간호관리": "간호",
        "기능회복": "기능"
    }


class RequiredFields:
    """필수 항목 필드명 정의"""
    # 기본정보 필드
    BASIC_INFO_FIELDS = {
        "총시간": "total_service_time",
        "시작시간": "start_time",
        "종료시간": "end_time",
        "이동서비스": "transport_service",
        "차량번호": "transport_vehicles"
    }
    
    # 신체활동지원 필드
    PHYSICAL_ACTIVITY_FIELDS = {
        "청결": "hygiene_care",
        "점심": "meal_lunch",
        "저녁": "meal_dinner",
        "화장실": "toilet_care",
        "이동도움": "mobility_care",
        "특이사항": "physical_note"
    }
    
    # 인지관리 필드
    COGNITIVE_CARE_FIELDS = {
        "인지관리": "cog_support",
        "의사소통": "comm_support",
        "특이사항": "cognitive_note"
    }
    
    # 간호관리 필드
    NURSING_CARE_FIELDS = {
        "혈압/체온": "bp_temp",
        "건강관리": "health_manage",
        "특이사항": "nursing_note"
    }
    
    # 기능회복 필드
    FUNCTIONAL_RECOVERY_FIELDS = {
        "향상프로그램": "prog_basic",
        "일상생활훈련": "prog_activity",
        "인지활동프로그램": "prog_cognitive",
        "인지기능향상": "prog_therapy",
        "특이사항": "functional_note"
    }


class WriterFields:
    """작성자 필드명 정의"""
    WRITER_MAPPING = {
        CategoryType.BASIC_INFO.value: ["writer_phy", "writer_nur", "writer_cog", "writer_func"],
        CategoryType.PHYSICAL_ACTIVITY.value: ["writer_phy"],
        CategoryType.COGNITIVE_CARE.value: ["writer_cog"],
        CategoryType.NURSING_CARE.value: ["writer_nur"],
        CategoryType.FUNCTIONAL_RECOVERY.value: ["writer_func"]
    }


class OptionalFields:
    """선택적 필드명 정의 (필수 항목 외 나머지 모든 필드)"""
    # 기본정보 선택적 필드
    BASIC_INFO_OPTIONAL = {}  # 차량번호는 필수 항목으로 이동
    
    # 신체활동지원 선택적 필드
    PHYSICAL_ACTIVITY_OPTIONAL = {
        "목욕 시간": "bath_time",
        "목욕 방법": "bath_method",
        "아침": "meal_breakfast"
    }
    
    # 인지관리 선택적 필드 (없음, 모두 필수)
    COGNITIVE_CARE_OPTIONAL = {}
    
    # 간호관리 선택적 필드
    NURSING_CARE_OPTIONAL = {
        "간호관리": "nursing_manage",
        "응급서비스": "emergency"
    }
    
    # 기능회복 선택적 필드
    FUNCTIONAL_RECOVERY_OPTIONAL = {
        "물리치료": "prog_therapy"
    }
    
    # 고객 정보 필드
    CUSTOMER_INFO = {
        "생년월일": "customer_birth_date",
        "요양등급": "customer_grade",
        "인식번호": "customer_recognition_no",
        "시설명": "facility_name",
        "시설코드": "facility_code"
    }
    
    # 모든 선택적 필드를 하나로 모음
    ALL_OPTIONAL_FIELDS = {
        **BASIC_INFO_OPTIONAL,
        **PHYSICAL_ACTIVITY_OPTIONAL,
        **COGNITIVE_CARE_OPTIONAL,
        **NURSING_CARE_OPTIONAL,
        **FUNCTIONAL_RECOVERY_OPTIONAL,
        **CUSTOMER_INFO
    }


class WeeklyDisplayFields:
    """주간상태변화평가 표시 필드명 정의"""
    # 기본정보 필드
    BASIC_INFO_DISPLAY = {
        "날짜": "date",
        "총시간": "total_service_time",
        "시작시간": "start_time",
        "종료시간": "end_time",
        "이동서비스": "transport_service",
        "차량번호": "transport_vehicles"
    }
    
    # 신체활동지원 필드 (상세)
    PHYSICAL_ACTIVITY_DISPLAY = {
        "날짜": "date",
        "특이사항": "physical_note",
        "세면/구강": "hygiene_care",
        "목욕": "bath_time",
        "식사": "meal_combined",
        "화장실이용하기(기저귀교환)": "toilet_care",
        "이동": "mobility_care",
        "작성자": "writer_phy"
    }
    
    # 인지관리 필드
    COGNITIVE_CARE_DISPLAY = {
        "날짜": "date",
        "특이사항": "cognitive_note",
        "인지관리지원": "cog_support",
        "의사소통도움": "comm_support",
        "작성자": "writer_cog"
    }
    
    # 간호관리 필드
    NURSING_CARE_DISPLAY = {
        "날짜": "date",
        "특이사항": "nursing_note",
        "혈압/체온": "bp_temp",
        "건강관리(5분)": "health_manage",
        "간호관리": "nursing_manage",
        "응급서비스": "emergency",
        "작성자": "writer_nur"
    }
    
    # 기능회복 필드
    FUNCTIONAL_RECOVERY_DISPLAY = {
        "날짜": "date",
        "특이사항": "functional_note",
        "향상 프로그램 내용": "prog_enhance_detail",
        "향상 프로그램 여부": "prog_basic",
        "인지활동 프로그램": "prog_activity",
        "인지기능 훈련": "prog_cognitive",
        "물리치료": "prog_therapy",
        "작성자": "writer_func"
    }
