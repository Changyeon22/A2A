# tools/planning_tool/core.py
"""
기획 문서 생성, 협업, Notion 문서 요약 및 확장 기능을 제공하는 도구 모듈입니다.

이 모듈은 여러 AI 페르소나를 활용하여 기획 문서를 작성하고, 이를 Notion에 저장하는 기능을 제공합니다.
또한 Notion에 저장된 문서를 검색하고, 요약하거나 확장하는 기능도 포함되어 있습니다.

표준 도구 인터페이스:
- TOOL_SCHEMAS: 이 모듈이 제공하는 모든 도구 함수의 스키마 목록
- TOOL_MAP: 함수 이름과 실제 실행 함수의 매핑

각 함수는 표준화된 타입 힌트와 문서화를 제공합니다.
"""

import os
import time
import logging
import traceback
from typing import Dict, List, Any, Optional, Tuple

import openai
from openai import OpenAI

from tools.notion_utils import upload_to_notion, search_notion_pages_by_keyword, get_page_content
from tools.planning_tool.prompts import (
    generate_create_document_prompt,
    generate_initial_prompt,
    generate_feedback_prompt,
    generate_final_prompt,
    generate_task_allocation_prompt,
    generate_task_integration_prompt,
    generate_task_review_prompt,
    generate_task_final_prompt,
    generate_summary_prompt,
    generate_expansion_prompt
)
from tools.planning_tool.configs import personas, DOCUMENT_TEMPLATES

# OpenAI 클라이언트 초기화
client = OpenAI()

# 로거 설정
logger = logging.getLogger(__name__)

# 로그 레벨 설정 (개발 환경에서는 DEBUG, 프로덕션에서는 INFO로 설정할 수 있습니다)
logger.setLevel(logging.INFO)

# 이 함수는 planning_tool 내부에서만 사용되므로 여기에 정의합니다.
def _persona_to_description(persona: Dict[str, Any]) -> str:
    """
    페르소나 딕셔너리 정보를 사람이 읽기 쉬운 문자열로 변환합니다.
    """
    desc = f"""직책: {persona.get('직책', '')}
전문 분야: {persona.get('전문 분야', '')}
업무 영역: {'; '.join(persona.get('업무 영역', []))}
사고방식: {'; '.join(persona.get('사고방식', []))}
"""
    return desc

# --- 도구의 실제 실행 함수 1: 신규 기획 문서 생성 (기존 execute_create_planning_document) ---
def execute_create_new_planning_document(user_input: str, writer_persona_name: str, reviewer_persona_name: str, template_name: str) -> Dict[str, Any]:
    """
    사용자 요구사항에 따라 새로운 기획 문서를 생성하고 Notion에 업로드합니다.
    
    Args:
        user_input (str): 기획 문서 작성을 위한 사용자의 구체적인 요구사항 또는 주제.
        writer_persona_name (str): 기획 문서를 작성할 AI 페르소나의 이름. (configs.py에 정의된 이름)
        reviewer_persona_name (str): 생성된 초안에 피드백을 제공할 AI 페르소나의 이름. (configs.py에 정의된 이름)
        template_name (str): 생성할 문서의 템플릿 종류. (configs.py의 DOCUMENT_TEMPLATES에 정의된 이름)
    
    Returns:
        Dict[str, Any]: 작업 결과를 담은 딕셔너리
            - status (str): 'success', 'error' 상태 값
            - message (str): 결과 메시지
            - notion_url (str, optional): 성공 시 생성된 문서의 Notion URL
    """
    logger.info(f"신규 기획 문서 생성 요청: {user_input}, 작성자: {writer_persona_name}, 피드백: {reviewer_persona_name}, 템플릿: {template_name}")

    # 유효성 검사
    if not user_input or not user_input.strip():
        return {"status": "error", "message": "사용자 입력이 비어있습니다. 기획 내용을 입력해주세요."}
    if writer_persona_name not in personas or reviewer_persona_name not in personas:
        return {"status": "error", "message": f"유효하지 않은 작성자 또는 피드백 담당자 페르소나 이름입니다. 현재 사용 가능한 페르소나: {', '.join(list(personas.keys()))}"}
    if template_name not in DOCUMENT_TEMPLATES:
        return {"status": "error", "message": f"유효하지 않은 문서 템플릿 이름입니다. 현재 사용 가능한 템플릿: {', '.join(list(DOCUMENT_TEMPLATES.keys()))}"}

    writer_persona = personas[writer_persona_name]
    reviewer_persona = personas[reviewer_persona_name]
    sections = DOCUMENT_TEMPLATES[template_name]
    
    try:
        # 1. 초안 생성
        writer_persona_info = f"너는 '{writer_persona_name}' [{writer_persona['직책']}] 페르소나야.\n{_persona_to_description(writer_persona)}"
        prompt = generate_create_document_prompt(
            user_input=user_input,
            writer_persona=writer_persona,
            template_name=template_name,
            template_structure=sections
        )
        draft_response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": prompt}], max_tokens=1800)
        draft = draft_response.choices[0].message.content

        # 2. 피드백 생성
        reviewer_persona_info = f"너는 '{reviewer_persona_name}' [{reviewer_persona['직책']}] 페르소나야.\n{_persona_to_description(reviewer_persona)}"
        prompt = generate_feedback_prompt(
            persona_info=reviewer_persona_info,
            draft_text=draft
        )
        feedback_response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": prompt}], max_tokens=1000)
        feedback = feedback_response.choices[0].message.content

        # 3. 최종 문서 생성
        writer_persona_info = f"너는 '{writer_persona_name}' [{writer_persona['직책']}] 페르소나야.\n{_persona_to_description(writer_persona)}"
        final_prompt = generate_final_prompt(
            persona_info=writer_persona_info,
            feedback_text=feedback
        )
        final_doc_response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": final_prompt}], max_tokens=2000)
        final_doc = final_doc_response.choices[0].message.content

        # 4. 노션 업로드
        title_suffix = f" - {user_input[:40]}..." if len(user_input) > 40 else f" - {user_input}"
        title = f"{template_name} ({writer_persona_name} 최종본){title_suffix}"
        
        success, result_message = upload_to_notion(title=title, content=final_doc)
        if success:
            return {"status": "success", "message": f"'{title}' 기획서가 Notion에 성공적으로 생성되었습니다. Notion에서 확인: {result_message}", "notion_url": result_message, "draft": draft, "feedback": feedback, "final_doc": final_doc}
        else:
            return {"status": "error", "message": f"Notion 저장 실패: {result_message}. 자세한 오류: {result_message}", "draft": draft, "feedback": feedback, "final_doc": final_doc}
            
    except openai.APIError as e:
        return {"status": "error", "message": f"OpenAI API 호출 중 오류가 발생했습니다: {e}"}
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"기획서 생성 중 예상치 못한 오류 발생: {e}\n{error_trace}")
        return {"status": "error", "message": f"기획서 생성 중 예상치 못한 오류 발생: {e}"}

# --- 도구의 실제 실행 함수 2: 다중 페르소나 협업 자동화 (tab_collaboration에서 가져옴) ---
def execute_collaboration_planning(
    project_title: str,
    base_document_type: str,
    user_requirements: str,
    writer_persona_name: str,
    allocate_to_persona_names: List[str],
    review_by_persona_name: str
) -> Dict[str, Any]:
    """
    주어진 요구사항을 기반으로 다중 페르소나 협업을 시뮬레이션하고 프로젝트 계획을 생성하여 Notion에 업로드합니다.
    
    Args:
        project_title (str): 프로젝트의 제목.
        base_document_type (str): 협업 계획의 기반이 될 문서 템플릿 타입.
        user_requirements (str): 프로젝트 계획 작성을 위한 구체적인 사용자 요구사항.
        writer_persona_name (str): 프로젝트 계획 초안을 작성할 AI 페르소나의 이름.
        allocate_to_persona_names (List[str]): 업무를 분배할 AI 페르소나 이름 목록 (2개 이상).
        review_by_persona_name (str): 최종 계획을 검토할 페르소나 이름.
    
    Returns:
        Dict[str, Any]: 작업 결과를 담은 딕셔너리
            - status (str): 'success', 'error' 상태 값
            - message (str): 결과 메시지
            - notion_url (str, optional): 성공 시 생성된 문서의 Notion URL
    """
    logger.info(f"협업 계획 생성 요청: {project_title}")
    
    # 유효성 검사
    invalid_personas = [p for p in allocate_to_persona_names if p not in personas]
    if invalid_personas:
        return {"status": "error", "message": f"유효하지 않은 업무 할당 페르소나 이름이 포함되어 있습니다: {', '.join(invalid_personas)}. 사용 가능한 페르소나: {', '.join(list(personas.keys()))}"}
    if review_by_persona_name not in personas:
        return {"status": "error", "message": f"유효하지 않은 검토 페르소나 이름입니다. 사용 가능한 페르소나: {', '.join(list(personas.keys()))}"}
    if writer_persona_name not in personas:
        return {"status": "error", "message": f"유효하지 않은 작성자 페르소나 이름입니다. 사용 가능한 페르소나: {', '.join(list(personas.keys()))}"}
    if base_document_type not in DOCUMENT_TEMPLATES:
         return {"status": "error", "message": f"유효하지 않은 문서 템플릿 타입입니다. 사용 가능한 템플릿: {', '.join(list(DOCUMENT_TEMPLATES.keys()))}"}
    if len(allocate_to_persona_names) < 2:
        return {"status": "error", "message": "업무를 분배할 페르소나는 최소 2개 이상 지정해야 합니다."}

    try:
        writer_persona = personas[writer_persona_name]
        sections = DOCUMENT_TEMPLATES[base_document_type]

        # 0. 프로젝트 계획서 초안 생성 (tab_collaboration의 1번 단계)
        initial_draft_prompt = generate_initial_prompt(
            persona_info=f"너는 '{writer_persona_name}' [{writer_persona['직책']}] 페르소나야.\n{_persona_to_description(writer_persona)}",
            sections=sections
        )
        initial_draft_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": initial_draft_prompt}],
            max_tokens=2000
        )
        initial_draft = initial_draft_response.choices[0].message.content
        logger.debug(f"Initial Project Draft generated.")

        # 1. 각 페르소나에게 업무 분배 시뮬레이션
        allocated_tasks = []
        for p_name in allocate_to_persona_names:
            persona = personas[p_name]
            persona_info = f"너는 '{p_name}' [{persona['직책']}] 페르소나야.\n{_persona_to_description(persona)}"
            task_allocation_prompt = generate_task_allocation_prompt(
                persona_info=persona_info, 
                document_content=initial_draft, 
                role=persona.get('직책', 'Unknown')
            )
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": task_allocation_prompt}],
                max_tokens=1500
            )
            tasks = response.choices[0].message.content
            allocated_tasks.append(f"### {p_name} ({persona['직책']}):\n{tasks}\n\n") # 형식 통일
        
        tasks_combined = "\n".join(allocated_tasks)
        logger.debug(f"Allocated tasks: {tasks_combined[:200]}...")

        # 2. 통합 프로젝트 계획서 생성
        integrator_persona_info = f"너는 '{writer_persona_name}' [{writer_persona['직책']}] 페르소나야.\n{_persona_to_description(writer_persona)}"
        integration_prompt = generate_task_integration_prompt(
            persona_info=integrator_persona_info, 
            task_lists=tasks_combined, 
            project_title=project_title
        )
        integrated_plan_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": integration_prompt}],
            max_tokens=3000
        )
        integrated_plan = integrated_plan_response.choices[0].message.content
        logger.debug(f"Integrated plan: {integrated_plan[:200]}...")

        # 3. 계획서 검토
        reviewer_persona_obj = personas[review_by_persona_name]
        reviewer_persona_info = f"너는 '{review_by_persona_name}' [{reviewer_persona_obj['직책']}] 페르소나야.\n{_persona_to_description(reviewer_persona_obj)}"
        reviewer_prompt = generate_task_review_prompt(
            persona_info=reviewer_persona_info, 
            plan_content=integrated_plan
        )
        review_feedback_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": reviewer_prompt}],
            max_tokens=1000
        )
        review_feedback = review_feedback_response.choices[0].message.content
        logger.debug(f"Review feedback: {review_feedback[:200]}...")

        # 4. 최종 계획서 수정
        final_integrator_persona_info = f"너는 '{writer_persona_name}' [{writer_persona['직책']}] 페르소나야.\n{_persona_to_description(writer_persona)}"
        final_prompt = generate_task_final_prompt(
            persona_info=final_integrator_persona_info, 
            feedback_text=review_feedback, 
            original_plan=integrated_plan
        )
        final_plan_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": final_prompt}],
            max_tokens=3000
        )
        final_plan = final_plan_response.choices[0].message.content
        logger.debug(f"Final plan: {final_plan[:200]}...")

        # 5. 노션 업로드
        title = f"협업 프로젝트 계획서: {project_title} ({writer_persona_name} 최종본)"
        success, result_message = upload_to_notion(title=title, content=final_plan)
        
        if success:
            return {"status": "success", "message": f"'{title}' 프로젝트 계획서가 Notion에 성공적으로 생성되었습니다. Notion에서 확인: {result_message}", "notion_url": result_message}
        else:
            return {"status": "error", "message": f"Notion 저장 실패: {result_message}. 자세한 오류: {result_message}"}
    
    except openai.APIError as e:
        return {"status": "error", "message": f"OpenAI API 호출 중 오류가 발생했습니다: {e}"}
    except Exception as e:
        return {"status": "error", "message": f"협업 계획 생성 중 예상치 못한 오류 발생: {e}"}


# --- 도구의 실제 실행 함수 3: Notion 문서 요약 (tab_summary에서 가져옴) ---
def execute_summarize_notion_document(keyword: str) -> Dict[str, Any]:
    """
    Notion에서 특정 키워드로 문서를 검색하고, 가장 최근에 수정된 문서의 내용을 요약합니다.
    
    Args:
        keyword (str): Notion 문서 검색에 사용할 키워드.
        
    Returns:
        Dict[str, Any]: 작업 성공 여부, 원본 문서 제목, 요약 내용, Notion URL을 포함하는 딕셔너리.
            - status (str): 'success' 또는 'error'
            - message (str): 결과에 대한 설명
            - title (str, optional): 검색된 문서 제목
            - summary (str, optional): 요약된 내용
            - notion_url (str, optional): 원본 문서 URL
    """
    logger.info(f"Notion 문서 요약 요청 (키워드: {keyword})")
    
    # 빈 키워드 검증
    if not keyword or not keyword.strip():
        return {"status": "error", "message": "키워드를 입력해주세요."}
    
    try:
        search_results = search_notion_pages_by_keyword(keyword)
        if not search_results:
            return {"status": "info", "message": f"'{keyword}'에 해당하는 Notion 문서를 찾을 수 없습니다."}
        
        target_page_id = search_results[0]['id']
        target_page_title = search_results[0]['title']
        
        logger.debug(f"Found Notion document for summary: {target_page_title} (ID: {target_page_id})")

        document_content = get_page_content(target_page_id)
        if not document_content:
            return {"status": "error", "message": f"'{target_page_title}' 문서의 내용을 가져올 수 없습니다. Notion 권한 문제일 수 있습니다."}
        
        summary_prompt = generate_summary_prompt(
            document_title=target_page_title, 
            document_content=document_content
        )
        
        summary_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": summary_prompt}],
            max_tokens=500
        )
        summary_text = summary_response.choices[0].message.content
        
        return {
            "status": "success", 
            "message": f"'{target_page_title}' 문서의 요약입니다: {summary_text}", 
            "title": target_page_title,
            "summary": summary_text, 
            "original_notion_url": f"https://www.notion.so/{target_page_id.replace('-', '')}"
        }
    
    except openai.APIError as e:
        return {"status": "error", "message": f"OpenAI API 호출 중 오류가 발생했습니다: {e}"}
    except Exception as e:
        return {"status": "error", "message": f"Notion 문서 요약 중 예상치 못한 오류 발생: {e}"}

# --- 도구의 실제 실행 함수 4: Notion 문서 확장/생성 (tab_summary에서 가져옴) ---
def execute_expand_notion_document(
    keyword: str,
    new_doc_type: str,
    extra_requirements: str,
    writer_persona_name: str
) -> Dict[str, Any]:
    """
    Notion에서 특정 키워드로 문서를 검색하고, 해당 내용을 기반으로 새로운 형식의 문서를 생성하거나 기존 문서를 확장합니다.
    새로 생성된 문서는 Notion에 업로드됩니다.
    
    Args:
        keyword (str): 참조할 기존 Notion 문서의 키워드.
        new_doc_type (str): 새로 생성할 문서의 템플릿 종류.
        extra_requirements (str): 새로운 문서 작성을 위한 추가 요구사항.
        writer_persona_name (str): 새로운 문서를 작성할 페르소나 이름.
        
    Returns:
        Dict[str, Any]: 작업 결과를 담은 딕셔너리
            - status (str): 'success', 'error', 'info' 중 하나
            - message (str): 결과 메시지
            - notion_url (str, optional): 성공 시 생성된 문서의 Notion URL
    """
    logger.info(f"Notion 문서 확장 요청 (키워드: {keyword}, 새 타입: {new_doc_type})")

    # 유효성 검사
    if not keyword or not keyword.strip():
        return {"status": "error", "message": "키워드를 입력해주세요."}
    if new_doc_type not in DOCUMENT_TEMPLATES:
        return {"status": "error", "message": f"유효하지 않은 신규 문서 타입입니다. 사용 가능한 템플릿: {', '.join(list(DOCUMENT_TEMPLATES.keys()))}"}
    if writer_persona_name not in personas:
        return {"status": "error", "message": f"유효하지 않은 작성자 페르소나 이름입니다. 사용 가능한 페르소나: {', '.join(list(personas.keys()))}"}

    try:
        # 1. Notion에서 참조 문서 검색 및 내용 가져오기
        search_results = search_notion_pages_by_keyword(keyword)
        if not search_results:
            return {"status": "info", "message": f"'{keyword}'에 해당하는 참조 Notion 문서를 찾을 수 없습니다. 문서 확장 작업을 시작할 수 없습니다."}
        
        target_page_id = search_results[0]['id']
        target_page_title = search_results[0]['title']
        document_content = get_page_content(target_page_id)
        
        if not document_content:
            return {"status": "error", "message": f"'{target_page_title}' 참조 문서의 내용을 가져올 수 없습니다. 권한 문제일 수 있습니다."}
        
        logger.debug(f"Retrieved reference document content length: {len(document_content)}")

        writer = personas[writer_persona_name]
        sections_to_expand = DOCUMENT_TEMPLATES[new_doc_type]

        # 2. LLM을 사용하여 문서 확장/생성
        expansion_prompt = generate_expansion_prompt(
            document_title=target_page_title, 
            document_content=document_content, 
            new_doc_type=new_doc_type, 
            sections_to_expand=sections_to_expand, 
            extra_requirements=extra_requirements
        )
        
        final_doc_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": expansion_prompt}],
            max_tokens=3000
        )
        final_doc_content = final_doc_response.choices[0].message.content

        # 3. 노션 업로드
        title = f"{new_doc_type} (참조: {target_page_title}) - {extra_requirements[:30]}..."
        success, result_message = upload_to_notion(title=title, content=final_doc_content)
        
        if success:
            return {"status": "success", "message": f"'{title}' 문서가 Notion에 성공적으로 확장 및 생성되었습니다. Notion에서 확인: {result_message}", "notion_url": result_message}
        else:
            return {"status": "error", "message": f"Notion 저장 실패: {result_message}. 자세한 오류: {result_message}"}

    except openai.APIError as e:
        return {"status": "error", "message": f"OpenAI API 호출 중 오류가 발생했습니다: {e}"}
    except Exception as e:
        return {"status": "error", "message": f"문서 확장 중 예상치 못한 오류 발생: {e}"}


# --- 모든 기능에 대한 OpenAI Function Calling 스키마 정의 ---
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "create_new_planning_document",
            "description": "새로운 기획 문서를 처음부터 생성하고 Notion에 저장합니다. 작성자, 피드백 담당자 페르소나와 문서 템플릿을 선택하여 기획 과정을 자동화합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_input": {
                        "type": "string",
                        "description": "기획 문서 작성을 위한 사용자의 구체적인 요구사항 또는 주제입니다. 반드시 구체적인 내용을 포함해야 합니다. (예: '신규 유저 유입 이벤트 기획서 작성')",
                    },
                    "writer_persona_name": {
                        "type": "string",
                        "description": "기획 문서를 작성할 AI 페르소나의 이름입니다. 다음 중 하나를 선택하세요: " + ", ".join(list(personas.keys())),
                        "enum": list(personas.keys())
                    },
                    "reviewer_persona_name": {
                        "type": "string",
                        "description": "생성된 초안에 피드백을 제공할 AI 페르소나의 이름입니다. 다음 중 하나를 선택하세요: " + ", ".join(list(personas.keys())),
                        "enum": list(personas.keys())
                    },
                    "template_name": {
                        "type": "string",
                        "description": "생성할 문서의 템플릿 종류입니다. 다음 중 하나를 선택하세요: " + ", ".join(list(DOCUMENT_TEMPLATES.keys())),
                        "enum": list(DOCUMENT_TEMPLATES.keys())
                    },
                },
                "required": ["user_input", "writer_persona_name", "reviewer_persona_name", "template_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "collaborate_on_planning",
            "description": "다양한 AI 페르소나를 활용하여 프로젝트 계획을 공동으로 수립하고 검토합니다. 초안 작성, 업무 분배, 계획 통합, 피드백 반영의 복잡한 과정을 자동화하고 Notion에 업로드합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_title": {
                        "type": "string",
                        "description": "협업하여 생성할 프로젝트 계획의 제목입니다.",
                    },
                    "base_document_type": {
                        "type": "string",
                        "description": "프로젝트 계획 초안을 생성할 때 사용할 문서 템플릿 종류입니다. (예: '컨셉 기획서', '업무 분배서')",
                        "enum": list(DOCUMENT_TEMPLATES.keys()),
                    },
                    "user_requirements": {
                        "type": "string",
                        "description": "프로젝트 계획 작성을 위한 구체적인 요구사항이나 핵심 아이디어입니다.",
                    },
                    "writer_persona_name": {
                        "type": "string",
                        "description": "프로젝트 계획 초안을 작성할 AI 페르소나의 이름입니다.",
                        "enum": list(personas.keys()),
                    },
                    "allocate_to_persona_names": {
                        "type": "array",
                        "items": {"type": "string", "enum": list(personas.keys())},
                        "description": "협업 과정에서 업무를 분배할 AI 페르소나 이름 목록입니다. 2개 이상의 페르소나를 지정해야 합니다.",
                        "minItems": 2
                    },
                    "review_by_persona_name": {
                        "type": "string",
                        "description": "최종 통합된 프로젝트 계획을 검토하고 피드백을 제공할 AI 페르소나의 이름입니다.",
                        "enum": list(personas.keys()),
                    },
                },
                "required": ["project_title", "base_document_type", "user_requirements", "writer_persona_name", "allocate_to_persona_names", "review_by_persona_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_notion_document",
            "description": "Notion에서 특정 키워드로 문서를 검색하고, 가장 최근에 수정된 문서의 내용을 핵심만 요약해줍니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Notion에서 검색할 문서의 키워드입니다. (예: '매출 보고서', '이벤트 기획')",
                    },
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "expand_notion_document",
            "description": "기존 Notion 문서를 참조하여 새로운 형식의 문서를 생성하거나 기존 문서를 확장합니다. 새로운 문서는 Notion에 업로드됩니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "참조할 기존 Notion 문서의 키워드입니다. (예: '기존 서비스 계획서')",
                    },
                    "new_doc_type": {
                        "type": "string",
                        "description": "새롭게 생성하거나 확장할 문서의 템플릿 종류입니다. (예: '컨셉 기획서', '상세 기획서', '업무 분배서')",
                        "enum": list(DOCUMENT_TEMPLATES.keys()),
                    },
                    "extra_requirements": {
                        "type": "string",
                        "description": "새로운 문서 작성을 위한 추가 요구사항 또는 구체적인 지시사항입니다.",
                    },
                     "writer_persona_name": {
                        "type": "string",
                        "description": "새로운 문서를 작성할 페르소나 이름입니다.",
                        "enum": list(personas.keys()),
                    },
                },
                "required": ["keyword", "new_doc_type", "extra_requirements", "writer_persona_name"],
            },
        },
    }
]

# --- 모든 함수를 매핑하는 하나의 딕셔너리 ---
TOOL_MAP = {
    "create_new_planning_document": execute_create_new_planning_document,
    "collaborate_on_planning": execute_collaboration_planning,
    "summarize_notion_document": execute_summarize_notion_document,
    "expand_notion_document": execute_expand_notion_document
}


# --- 표준 인터페이스 검증 함수 ---
def validate_tool_interface() -> bool:
    """
    planning_tool 모듈이 정의된 표준 인터페이스를 준수하는지 검증합니다.
    - TOOL_SCHEMAS에 정의된 모든 함수가 TOOL_MAP에 존재하는지 확인
    - TOOL_MAP의 모든 함수가 실제로 구현되어 있는지 확인
    
    Returns:
        bool: 검증 결과 (True: 준수함, False: 준수하지 않음)
    """
    try:
        # 1. 모든 스키마 함수가 매핑에 존재하는지 확인
        schema_function_names = [schema["function"]["name"] for schema in TOOL_SCHEMAS if "function" in schema]
        for name in schema_function_names:
            if name not in TOOL_MAP:
                logger.error(f"스키마에 정의된 함수 '{name}'가 TOOL_MAP에 없습니다.")
                return False
        
        # 2. 모든 매핑이 유효한 함수를 가리키는지 확인
        for name, func in TOOL_MAP.items():
            if not callable(func):
                logger.error(f"TOOL_MAP의 '{name}' 항목이 호출 가능한 함수가 아닙니다.")
                return False
            
            # 3. 스키마에 해당 함수가 정의되어 있는지 확인
            if name not in schema_function_names:
                logger.error(f"TOOL_MAP의 '{name}' 함수가 스키마에 정의되어 있지 않습니다.")
                return False
        
        logger.info("planning_tool 모듈이 표준 인터페이스를 준수합니다.")
        return True
        
    except Exception as e:
        logger.error(f"인터페이스 검증 중 오류 발생: {e}\n{traceback.format_exc()}")
        return False


# 모듈 로드 시 자동 검증 실행
if __name__ != "__main__":
    validate_tool_interface()