"""
문서 템플릿 생성 도구 핵심 기능

이 모듈은 다양한 문서 유형에 적합한 템플릿을 생성하는 기능을 제공합니다.
"""
import os
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 기본 템플릿 정의
DEFAULT_TEMPLATES = {
    "report": {
        "title": "# {title}\n\n",
        "summary": "## 요약\n{summary}\n\n",
        "methodology": "## 연구 방법론\n{methodology}\n\n",
        "findings": "## 주요 조사 결과\n{findings}\n\n",
        "recommendations": "## 권장 사항\n{recommendations}\n\n",
        "conclusion": "## 결론\n{conclusion}\n\n",
        "references": "## 참고 자료\n{references}\n\n"
    },
    "article": {
        "title": "# {title}\n\n",
        "author": "*저자: {author}*\n\n",
        "abstract": "**초록:** {abstract}\n\n",
        "introduction": "## 서론\n{introduction}\n\n",
        "body": "## 본문\n{body}\n\n",
        "conclusion": "## 결론\n{conclusion}\n\n",
        "references": "## 참고 문헌\n{references}\n\n"
    },
    "memo": {
        "title": "# {title}\n\n",
        "date": "날짜: {date}\n",
        "to": "수신: {to}\n",
        "from": "발신: {from}\n\n",
        "message": "---\n\n{message}\n\n"
    },
    "research": {
        "title": "# {title}\n\n",
        "background": "## 배경\n{background}\n\n",
        "objectives": "## 연구 목적\n{objectives}\n\n",
        "methods": "## 연구 방법\n{methods}\n\n",
        "results": "## 연구 결과\n{results}\n\n",
        "discussion": "## 논의\n{discussion}\n\n",
        "conclusion": "## 결론\n{conclusion}\n\n",
        "references": "## 참고 문헌\n{references}\n\n"
    },
    "proposal": {
        "title": "# {title}\n\n",
        "executive_summary": "## 개요\n{executive_summary}\n\n",
        "problem_statement": "## 문제 정의\n{problem_statement}\n\n",
        "proposed_solution": "## 제안 솔루션\n{proposed_solution}\n\n",
        "timeline": "## 일정\n{timeline}\n\n",
        "budget": "## 예산\n{budget}\n\n",
        "expected_outcomes": "## 예상 결과\n{expected_outcomes}\n\n",
        "conclusion": "## 결론\n{conclusion}\n\n"
    },
    "tech_doc": {
        "title": "# {title}\n\n",
        "overview": "## 개요\n{overview}\n\n",
        "architecture": "## 아키텍처\n{architecture}\n\n",
        "components": "## 구성 요소\n{components}\n\n",
        "api": "## API 설명\n{api}\n\n",
        "usage_examples": "## 사용 예제\n{usage_examples}\n\n",
        "troubleshooting": "## 문제 해결\n{troubleshooting}\n\n",
        "references": "## 참고 자료\n{references}\n\n"
    }
}

def generate_template(template_type: str) -> Dict[str, Any]:
    """
    지정된 유형의 문서 템플릿을 생성합니다.
    
    Args:
        template_type: 템플릿 유형 ('report', 'article', 'memo' 등)
        
    Returns:
        템플릿 데이터
    """
    logger.info(f"Generating template for type: {template_type}")
    
    # 입력 검증 추가
    if not template_type or not isinstance(template_type, str):
        return {
            "status": "error",
            "message": "Invalid template type provided"
        }
    
    try:
        if template_type in DEFAULT_TEMPLATES:
            template = DEFAULT_TEMPLATES[template_type]
            return {
                "status": "success",
                "template": template,
                "template_type": template_type,
                "structure": {key: f"섹션: {key}" for key in template.keys()}
            }
        else:
            # 지원되지 않는 템플릿 유형인 경우 에러 반환
            logger.warning(f"Template type '{template_type}' not found")
            return {
                "status": "error",
                "message": f"Template type '{template_type}' is not supported"
            }
            
    except Exception as e:
        logger.error(f"Error generating template: {str(e)}")
        return {
            "status": "error",
            "message": f"Template generation failed: {str(e)}"
        }

def get_available_templates() -> Dict[str, Any]:
    """
    사용 가능한 모든 템플릿 목록을 반환합니다.
    
    Returns:
        템플릿 목록과 상태 정보
    """
    try:
        templates = list(DEFAULT_TEMPLATES.keys())
        return {
            "status": "success",
            "templates": templates,
            "count": len(templates)
        }
    except Exception as e:
        logger.error(f"Error getting available templates: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get available templates: {str(e)}"
        }

def get_template_structure(template_type: str) -> Dict[str, Any]:
    """
    특정 템플릿의 구조를 반환합니다.
    
    Args:
        template_type: 템플릿 유형
        
    Returns:
        템플릿 구조와 상태 정보
    """
    try:
        if not template_type or not isinstance(template_type, str):
            return {
                "status": "error",
                "message": "Invalid template type provided"
            }
            
        if template_type not in DEFAULT_TEMPLATES:
            return {
                "status": "error",
                "message": f"Template type '{template_type}' not found"
            }
        
        template = DEFAULT_TEMPLATES[template_type]
        structure = {key: f"섹션: {key}" for key in template.keys()}
        
        return {
            "status": "success",
            "template_type": template_type,
            "structure": structure,
            "sections": list(template.keys())
        }
        
    except Exception as e:
        logger.error(f"Error getting template structure: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get template structure: {str(e)}"
        }

def customize_template(template_type: str, custom_sections: Dict[str, str]) -> Dict[str, Any]:
    """
    기본 템플릿을 사용자 정의합니다.
    
    Args:
        template_type: 기본 템플릿 유형
        custom_sections: 사용자 정의 섹션 정의
        
    Returns:
        사용자 정의된 템플릿
    """
    # 입력 검증 추가
    if not template_type or not isinstance(template_type, str):
        return {
            "status": "error",
            "message": "Invalid template type provided"
        }
    
    if custom_sections is None:
        return {
            "status": "error",
            "message": "Custom sections cannot be None"
        }
    
    if not isinstance(custom_sections, dict):
        return {
            "status": "error",
            "message": "Custom sections must be a dictionary"
        }
    
    if template_type not in DEFAULT_TEMPLATES:
        return {
            "status": "error",
            "message": f"Template type '{template_type}' not found"
        }
    
    try:
        base_template = DEFAULT_TEMPLATES[template_type].copy()
        
        # 사용자 정의 섹션 적용
        for section, format_string in custom_sections.items():
            if section in base_template:
                base_template[section] = format_string
            else:
                base_template[section] = f"## {section}\n{{{section}}}\n\n"
        
        return {
            "status": "success",
            "template": base_template,
            "template_type": f"custom_{template_type}",
            "message": "Template customized successfully"
        }
        
    except Exception as e:
        logger.error(f"Error customizing template: {str(e)}")
        return {
            "status": "error",
            "message": f"Template customization failed: {str(e)}"
        }


# --- LLM이 사용할 도구 명세 (TOOL_SCHEMAS) ---
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "generate_template",
            "description": "지정된 유형의 문서 템플릿을 생성합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "template_type": {
                        "type": "string",
                        "description": "템플릿 유형 ('report', 'article', 'memo', 'research' 등)",
                        "enum": ["report", "article", "memo", "research"]
                    }
                },
                "required": ["template_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_templates",
            "description": "사용 가능한 모든 템플릿 목록을 반환합니다.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_template_structure",
            "description": "특정 템플릿의 구조를 반환합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "template_type": {
                        "type": "string",
                        "description": "템플릿 유형",
                        "enum": ["report", "article", "memo", "research"]
                    }
                },
                "required": ["template_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "customize_template",
            "description": "기본 템플릿을 사용자 정의합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "template_type": {
                        "type": "string",
                        "description": "기본 템플릿 유형",
                        "enum": ["report", "article", "memo", "research"]
                    },
                    "custom_sections": {
                        "type": "object",
                        "description": "사용자 정의 섹션 정의",
                        "additionalProperties": {
                            "type": "string"
                        }
                    }
                },
                "required": ["template_type", "custom_sections"]
            }
        }
    }
]

# 도구 맵 (함수명과 실제 함수의 매핑)
TOOL_MAP = {
    "generate_template": generate_template,
    "get_available_templates": get_available_templates,
    "get_template_structure": get_template_structure,
    "customize_template": customize_template
}

def validate_tool_interface():
    """
    TOOL_SCHEMAS와 TOOL_MAP이 일치하는지 검증합니다.
    
    Returns:
        bool: 검증 성공 여부
    """
    try:
        schema_function_names = []
        for schema in TOOL_SCHEMAS:
            if "function" in schema and "name" in schema["function"]:
                schema_function_names.append(schema["function"]["name"])
        
        tool_map_names = set(TOOL_MAP.keys())
        schema_names = set(schema_function_names)
        
        missing_in_map = schema_names - tool_map_names
        missing_in_schema = tool_map_names - schema_names
        
        if missing_in_map:
            logger.error(f"TOOL_MAP에는 있지만 TOOL_SCHEMAS에는 없는 함수: {missing_in_map}")
            return False
            
        if missing_in_schema:
            logger.error(f"TOOL_SCHEMAS에는 있지만 TOOL_MAP에는 없는 함수: {missing_in_schema}")
            return False
            
        logger.info("도구 인터페이스 검증 성공")
        return True
        
    except Exception as e:
        logger.error(f"도구 인터페이스 검증 중 오류 발생: {str(e)}")
        return False
