"""
문서 서식 지정 도구 핵심 기능

이 모듈은 다양한 문서 유형에 적합한 서식을 지정하는 기능을 제공합니다.
"""
import os
import logging
import re
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_document(document_type: str, content: Dict[str, Any]) -> Dict[str, Any]:
    """
    문서 유형에 따라 적절한 서식을 적용합니다.
    
    Args:
        document_type: 문서 유형 ('report', 'article', 'memo' 등)
        content: 문서 내용을 담은 딕셔너리
        
    Returns:
        서식이 적용된 문서 데이터
    """
    logger.info(f"Formatting document of type: {document_type}")
    
    try:
        if document_type == "report":
            return format_report(content)
        elif document_type == "article":
            return format_article(content)
        elif document_type == "memo":
            return format_memo(content)
        else:
            # 기본 마크다운 형식 적용
            return format_markdown_document(content)
            
    except Exception as e:
        logger.error(f"Error formatting document: {str(e)}")
        return {
            "status": "error",
            "message": f"Document formatting failed: {str(e)}"
        }

def format_report(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    보고서 형식으로 문서를 포맷팅합니다.
    
    Args:
        content: 보고서 내용
        
    Returns:
        포맷팅된 보고서
    """
    title = content.get("title", "보고서")
    summary = content.get("summary", "")
    findings = content.get("findings", "")
    conclusion = content.get("conclusion", "")
    references = content.get("references", "")
    
    # 기본 보고서 양식 적용
    formatted_report = f"""# {title}

## 요약
{summary}

## 주요 조사 결과
{findings}

## 결론
{conclusion}

## 참고 자료
{references}
"""
    
    # 선택적 섹션 추가
    if "methodology" in content:
        methodology = content["methodology"]
        formatted_report = formatted_report.replace(
            "## 주요 조사 결과",
            f"## 연구 방법론\n{methodology}\n\n## 주요 조사 결과"
        )
        
    if "recommendations" in content:
        recommendations = content["recommendations"]
        formatted_report = formatted_report.replace(
            "## 결론",
            f"## 권장 사항\n{recommendations}\n\n## 결론"
        )
    
    return {
        "status": "success",
        "document": formatted_report,
        "document_type": "report",
        "title": title
    }

def format_article(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    기사 형식으로 문서를 포맷팅합니다.
    
    Args:
        content: 기사 내용
        
    Returns:
        포맷팅된 기사
    """
    title = content.get("title", "제목 없음")
    author = content.get("author", "")
    abstract = content.get("abstract", "")
    introduction = content.get("introduction", "")
    body = content.get("body", "")
    conclusion = content.get("conclusion", "")
    
    author_line = f"*저자: {author}*\n\n" if author else ""
    
    formatted_article = f"""# {title}

{author_line}**초록:** {abstract}

## 서론
{introduction}

## 본문
{body}

## 결론
{conclusion}
"""

    return {
        "status": "success",
        "document": formatted_article,
        "document_type": "article",
        "title": title
    }

def format_memo(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    메모 형식으로 문서를 포맷팅합니다.
    
    Args:
        content: 메모 내용
        
    Returns:
        포맷팅된 메모
    """
    title = content.get("title", "메모")
    date = content.get("date", "")
    to = content.get("to", "")
    from_person = content.get("from", "")
    message = content.get("message", "")
    
    date_line = f"날짜: {date}\n" if date else ""
    to_line = f"수신: {to}\n" if to else ""
    from_line = f"발신: {from_person}\n" if from_person else ""
    
    header = ""
    if date_line or to_line or from_line:
        header = f"""
{date_line}{to_line}{from_line}
---

"""

    formatted_memo = f"""# {title}
{header}
{message}
"""

    return {
        "status": "success",
        "document": formatted_memo,
        "document_type": "memo",
        "title": title
    }

def format_markdown_document(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    기본 마크다운 형식으로 문서를 포맷팅합니다.
    
    Args:
        content: 문서 내용
        
    Returns:
        포맷팅된 문서
    """
    title = content.get("title", "문서")
    document = f"# {title}\n\n"
    
    # title을 제외한 모든 키를 섹션으로 처리
    for key, value in content.items():
        if key != "title" and value:
            section_title = key.replace("_", " ").title()
            document += f"## {section_title}\n{value}\n\n"
    
    return {
        "status": "success",
        "document": document,
        "document_type": "markdown",
        "title": title
    }


# --- LLM이 사용할 도구 명세 (TOOL_SCHEMAS) ---
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "format_document",
            "description": "문서 유형에 따라 적절한 서식을 적용합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "document_type": {
                        "type": "string",
                        "description": "문서 유형 ('report', 'article', 'memo', 'markdown' 등)",
                        "enum": ["report", "article", "memo", "markdown"]
                    },
                    "content": {
                        "type": "object",
                        "description": "문서 내용을 담은 딕셔너리",
                        "properties": {
                            "title": {"type": "string", "description": "문서 제목"},
                            "author": {"type": "string", "description": "작성자"},
                            "content": {"type": "string", "description": "본문 내용"}
                        },
                        "required": ["title", "content"]
                    }
                },
                "required": ["document_type", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "format_report",
            "description": "보고서 형식으로 문서를 포맷팅합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "object",
                        "description": "보고서 내용",
                        "properties": {
                            "title": {"type": "string", "description": "보고서 제목"},
                            "summary": {"type": "string", "description": "요약"},
                            "findings": {"type": "string", "description": "주요 조사 결과"},
                            "recommendations": {"type": "string", "description": "권장 사항"},
                            "conclusion": {"type": "string", "description": "결론"}
                        },
                        "required": ["title"]
                    }
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "format_article",
            "description": "기사 형식으로 문서를 포맷팅합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "object",
                        "description": "기사 내용",
                        "properties": {
                            "title": {"type": "string", "description": "기사 제목"},
                            "author": {"type": "string", "description": "작성자"},
                            "abstract": {"type": "string", "description": "초록"},
                            "introduction": {"type": "string", "description": "서론"},
                            "body": {"type": "string", "description": "본문"},
                            "conclusion": {"type": "string", "description": "결론"}
                        },
                        "required": ["title", "author"]
                    }
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "format_memo",
            "description": "메모 형식으로 문서를 포맷팅합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "object",
                        "description": "메모 내용",
                        "properties": {
                            "title": {"type": "string", "description": "메모 제목"},
                            "message": {"type": "string", "description": "메모 내용"},
                            "to": {"type": "string", "description": "수신자"},
                            "from": {"type": "string", "description": "발신자"}
                        },
                        "required": ["title", "message"]
                    }
                },
                "required": ["content"]
            }
        }
    }
]

# 도구 맵 (함수명과 실제 함수의 매핑)
TOOL_MAP = {
    "format_document": format_document,
    "format_report": format_report,
    "format_article": format_article,
    "format_memo": format_memo
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
