# tools/persona_system.py
from .personas_db import personas

def get_persona_by_key(key: str):
    """키(영문/한글)로 페르소나 반환"""
    if key in personas:
        return personas[key]
    # 한글 키 지원
    for k, v in personas.items():
        if v.get("직책") == key or k == key:
            return v
    raise ValueError(f"해당 키의 페르소나가 없습니다: {key}")

def select_personas(context: dict, user_selected_keys: list = None):
    """
    컨텍스트 및 유저 선택 기반 페르소나 반환
    - user_selected_keys: 유저가 직접 선택한 페르소나 키 리스트
    - context: 자동 매칭용(업무 도메인, task_type, complexity 등)
    """
    if user_selected_keys:
        return [get_persona_by_key(k) for k in user_selected_keys]
    domain = context.get("domain")
    task_type = context.get("task_type")
    complexity = context.get("complexity", "중")

    # 개발 도메인
    if domain == "development":
        if task_type == "code_review":
            if complexity == "상":
                return [get_persona_by_key("senior_backend_dev"), get_persona_by_key("qa_engineer")]
            else:
                return [get_persona_by_key("backend_dev")]
        if task_type == "security_review":
            return [get_persona_by_key("backend_dev"), get_persona_by_key("security_expert")]
        if task_type == "api_design":
            return [get_persona_by_key("backend_dev"), get_persona_by_key("api_designer")]
        return [get_persona_by_key("backend_dev")]

    # 기획 도메인
    if domain == "planning":
        if task_type == "planning":
            return [get_persona_by_key("planner"), get_persona_by_key("pm")]
        if task_type == "requirement_analysis":
            return [get_persona_by_key("planner"), get_persona_by_key("ba")]
        return [get_persona_by_key("planner")]

    # 디자인 도메인
    if domain == "design":
        if task_type == "ui_design":
            return [get_persona_by_key("ui_designer"), get_persona_by_key("ux_researcher")]
        if task_type == "branding":
            return [get_persona_by_key("brand_designer")]
        return [get_persona_by_key("ui_designer")]

    # 마케팅 도메인
    if domain == "marketing":
        if task_type == "data_analysis":
            return [get_persona_by_key("growth_marketer"), get_persona_by_key("data_analyst")]
        if task_type == "content":
            return [get_persona_by_key("content_marketer")]
        return [get_persona_by_key("growth_marketer")]

    # 비즈니스/경영 도메인
    if domain == "business":
        if task_type == "strategy":
            return [get_persona_by_key("business_planner"), get_persona_by_key("pm")]
        return [get_persona_by_key("business_planner")]

    # 이메일, 요약 등 공통 업무
    if task_type == "email_response":
        return [get_persona_by_key("pm")]
    if task_type == "summarization":
        return [get_persona_by_key("planner")]

    # 기본값 (기획자)
    return [get_persona_by_key("planner")] 