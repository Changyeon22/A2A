from .configs import personas

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
    - context: 자동 매칭용(추후 확장)
    """
    if user_selected_keys:
        return [get_persona_by_key(k) for k in user_selected_keys]
    # 자동 매칭 로직(예시)
    domain = context.get("domain")
    if domain == "planning":
        return [get_persona_by_key("planner")]
    # ... 기타 규칙
    return [] 