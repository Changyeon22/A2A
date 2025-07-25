# tools/planning_tool/prompts.py

# planning_tool/configs.py에서 정의된 TEMPLATES 임포트
from .configs import DOCUMENT_TEMPLATES 

# --- 문서 생성 프롬프트 함수 추가 ---
def generate_create_document_prompt(user_input: str, writer_persona: dict, template_name: str, template_structure: list) -> str:
    """사용자 입력, 작성자 페르소나 정보, 템플릿을 기반으로 문서 생성 프롬프트를 생성합니다.
    
    Args:
        user_input: 사용자가 요청한 문서 주제/요구사항
        writer_persona: 문서 작성자 페르소나 정보 딕셔너리
        template_name: 템플릿 이름
        template_structure: 템플릿 구조 섹션 목록
        
    Returns:
        str: 문서 생성을 위한 프롬프트
    """
    persona_name = writer_persona.get('이름', '알 수 없음')
    persona_role = writer_persona.get('직책', '알 수 없음')
    persona_desc = f"직급: {writer_persona.get('직급', '알 수 없음')}\n전문분야: {writer_persona.get('전문분야', '알 수 없음')}\n성격: {writer_persona.get('성격', '알 수 없음')}\n글쓰기 특징: {writer_persona.get('글쓰기_특징', '알 수 없음')}"
    
    section_guide = "\n".join([f"- {s}" for s in template_structure])
    
    return f"""
너는 '{persona_name}' [{persona_role}] 페르소나야.
{persona_desc}

다음 요구사항에 따라 '{template_name}' 형식의 문서를 작성해 줘:
{user_input}

문서는 아래 섹션 구조에 맞게 작성해줘. 각 섹션은 명확히 구분하되, 자연스러운 문장과 페르소나의 스타일을 살려 작성해.
각 섹션에는 신뢰성, 근거, 예시, 한계, 참고자료 등을 자연스럽게 포함해주고, 복합 요구가 있을 경우 다른 페르소나와 협업한 결과도 반영해줘.
문서의 한계나 불확실성, 추가로 고려할 점이 있다면 마지막에 안내해줘.
모든 결과는 반드시 한글로 작성해줘!

[문서 섹션 구조]
{section_guide}
"""

# --- 신규 문서 생성 관련 프롬프트 (기존 prompts.py에서 가져옴) ---
def generate_initial_prompt(persona_info: str, sections: list) -> str:
    section_guide = "\n".join([f"- {s}" for s in sections])
    return f'''
{persona_info}

문서를 다음 섹션 구조에 맞게 작성해줘:
{section_guide}

모든 결과는 반드시 한글로 작성해줘!
'''

def generate_feedback_prompt(persona_info: str, draft_text: str) -> str:
    return f'''
{persona_info}

아래 초안을 읽고, 피드백을 작성해줘.
피드백에는 신뢰성, 정확성, 근거, 예시, 한계, 추가로 고려할 점 등을 자연스럽게 포함해줘.
필요하다면 다른 페르소나와 협업한 의견도 반영해줘.
모든 결과는 반드시 한글로 작성해줘!

[초안]
{draft_text}
'''

def generate_final_prompt(persona_info: str, feedback_text: str) -> str:
    return f'''
{persona_info}

아래 여러 페르소나의 피드백(요약/수정/제안 등)을 모두 반영하여 기획서 최종본을 작성해줘.
각 섹션은 명확히 구분하되, 자연스러운 문장과 페르소나의 스타일을 살려 작성해.
중복, 충돌, 누락이 없도록 검토하고, 신뢰성, 근거, 예시, 한계, 참고자료 등을 자연스럽게 포함해줘.
모든 결과는 반드시 한글로 작성해줘!

[피드백]
{feedback_text}
'''

# --- 다중 페르소나 협업 관련 프롬프트 (tab_collaboration.py에서 가져옴) ---
def generate_task_allocation_prompt(persona_info: str, document_content: str, role: str) -> str:
    return f'''
{persona_info}

아래 문서를 읽고, {role}의 관점에서 본인이 진행해야 할 업무를 리스트업해줘.
각 업무는 명확하게 구분해서 작성하고, 신뢰성, 근거, 한계, 추가로 고려할 점 등을 자연스럽게 포함해줘.
필요하다면 다른 역할과 협업한 결과도 반영해줘.
모든 결과는 반드시 한글로 작성해줘!

[문서]
{document_content}
'''

def generate_task_integration_prompt(persona_info: str, task_lists: str, project_title: str) -> str:
    return f'''
{persona_info}

각 페르소나의 업무 리스트를 읽고, 하나의 프로젝트 계획서로 취합해줘.
각 섹션은 명확히 구분하되, 자연스러운 문장과 페르소나의 스타일을 살려 작성해.
중복, 충돌, 누락이 없도록 검토하고, 신뢰성, 근거, 예시, 한계, 참고자료 등을 자연스럽게 포함해줘.
필요하다면 각 역할과 협업한 결과도 반영해줘.
모든 결과는 반드시 한글로 작성해줘!

[업무 리스트]
{task_lists}
[프로젝트 명칭: {project_title}]
'''

def generate_task_review_prompt(persona_info: str, plan_content: str) -> str:
    return f'''
{persona_info}

다음 프로젝트 계획서를 검토하고, 전문가적인 관점에서 피드백을 작성해줘.
피드백에는 신뢰성, 근거, 한계, 추가로 고려할 점 등을 자연스럽게 포함해줘.
필요하다면 다른 역할과 협업한 의견도 반영해줘.
모든 결과는 반드시 한글로 작성해줘!

[계획서]
{plan_content}
'''

def generate_task_final_prompt(persona_info: str, feedback_text: str, original_plan: str) -> str:
    return f'''
{persona_info}

아래 여러 페르소나의 피드백을 모두 반영하여 프로젝트 계획서를 수정해줘.
각 섹션은 명확히 구분하되, 자연스러운 문장과 페르소나의 스타일을 살려 작성해.
중복, 충돌, 누락이 없도록 검토하고, 신뢰성, 근거, 예시, 한계, 참고자료 등을 자연스럽게 포함해줘.
필요하다면 각 역할과 협업한 결과도 반영해줘.
모든 결과는 반드시 한글로 작성해줘!

[피드백]
{feedback_text}
[원래 계획서]
{original_plan}
'''

# --- 문서 요약 및 확장 관련 프롬프트 (tab_summary.py에서 가져옴) ---
def generate_summary_prompt(document_title: str, document_content: str) -> str:
    return f'''
다음 문서의 내용을 핵심만 요약해줘.
요약에는 신뢰성, 근거, 한계, 추가로 고려할 점 등을 자연스럽게 포함해줘.
모든 결과는 반드시 한글로 작성해줘!

문서 제목: {document_title}
문서 내용:
{document_content}
'''

def generate_expansion_prompt(document_title: str, document_content: str, new_doc_type: str, sections_to_expand: list, extra_requirements: str) -> str:
    sections_guide = "\n".join([f"- {s}" for s in sections_to_expand])
    return f'''
'{document_title}' 문서의 내용을 기반으로 새로운 문서 '{new_doc_type}'를 작성해줘.
특히 다음 섹션들을 상세하게 확장해서 작성해줘:
{sections_guide}

확장된 각 섹션에는 신뢰성, 근거, 예시, 한계, 참고자료 등을 자연스럽게 포함해주고, 복합 요구가 있을 경우 다른 페르소나와 협업한 결과도 반영해줘.
문서의 한계나 불확실성, 추가로 고려할 점이 있다면 마지막에 안내해줘.
모든 결과는 반드시 한글로 작성해줘!

기존 문서 내용:
{document_content}

추가 요구사항:
{extra_requirements}
'''