import logging
import traceback
import time
from typing import Dict, Any, Optional

import openai
from openai import OpenAI
# OpenAI SDK v1.x에서는 일반 예외 사용

# 모듈 내부 임포트
from .configs import (
    DEFAULT_MODEL, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE,
    DEFAULT_PROMPT_TEMPLATE, STATUS_SUCCESS, STATUS_ERROR,
    ERROR_EMPTY_TEXT, ERROR_API, ERROR_UNEXPECTED,
    LOG_START, LOG_EMPTY_TEXT, LOG_API_CALL, LOG_COMPLETE,
    LOG_API_ERROR, LOG_UNEXPECTED_ERROR, SYSTEM_MESSAGE
)
from .utils import prepare_text_for_summarization, create_summary_prompt

# OpenAI 클라이언트 초기화
# 클라이언트는 함수 내부에서 호출할 때마다 생성하여 환경변수를 읽어오도록 변경

# 로거 설정
logger = logging.getLogger(__name__)

def summarize_text(text_to_summarize: str, prompt_template: str = DEFAULT_PROMPT_TEMPLATE) -> Dict[str, Any]:
    """
    주어진 텍스트를 OpenAI API를 사용하여 요약합니다.
    재시도 로직이 포함되어 있어 API 속도 제한(rate limit) 오류 발생 시 자동으로 재시도합니다.

    Args:
        text_to_summarize (str): 요약할 텍스트 내용.
        prompt_template (str): 요약 프롬프트의 템플릿.

    Returns:
        dict: 상태와 요약 결과 또는 오류 메시지를 포함하는 딕셔너리.
    """
    logger.info(LOG_START)
    
    if not text_to_summarize or not text_to_summarize.strip():
        logger.warning(LOG_EMPTY_TEXT)
        return {"status": STATUS_ERROR, "message": ERROR_EMPTY_TEXT}

    # 재시도 설정
    max_retries = 5
    base_delay = 1  # 초 단위 기본 대기 시간
    
    # 텍스트 준비 및 프롬프트 생성 (재시도와 무관하게 한 번만 수행)
    truncated_text = prepare_text_for_summarization(text_to_summarize)
    full_prompt = create_summary_prompt(truncated_text, prompt_template)
    
    for attempt in range(max_retries):
        try:
            # OpenAI 클라이언트 초기화 - 함수 내부에서 호출할 때마다 생성
            # 환경 변수에서 API 키를 가져오도록 해서 보안성 강화
            try:
                import os
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    logger.error("OpenAI API 키가 환경변수에 없습니다")
                    return {"status": STATUS_ERROR, "message": "API 키 구성 오류"}
                    
                client = OpenAI(api_key=api_key)
            except Exception as setup_err:
                logger.error(f"OpenAI 클라이언트 초기화 오류: {setup_err}")
                return {"status": STATUS_ERROR, "message": f"API 클라이언트 초기화 오류: {setup_err}"}
            
            # OpenAI API 호출
            logger.info(f"{LOG_API_CALL} (시도 {attempt + 1}/{max_retries})")
            response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=DEFAULT_MAX_TOKENS,
                temperature=DEFAULT_TEMPERATURE,
            )

            summary = response.choices[0].message.content.strip()
            logger.info(LOG_COMPLETE)
            return {"status": STATUS_SUCCESS, "summary": summary}

        except Exception as e:
            # 에러 유형 검사
            error_str = str(e).lower()
            
            # 속도 제한(Rate Limit) 관련 오류
            if 'rate limit' in error_str or 'rate_limit' in error_str or 'too many requests' in error_str:
                wait_time = base_delay * (2 ** attempt)  # 지수 백오프
                error_msg = f"속도 제한(Rate Limit) 오류 발생: {e}. {wait_time}초 후 재시도합니다. (시도 {attempt + 1}/{max_retries})"
                logger.warning(error_msg)
                
                if attempt < max_retries - 1:  # 마지막 시도가 아니면 대기 후 재시도
                    time.sleep(wait_time)
                    continue
                else:  # 마지막 시도면 실패 반환
                    return {
                        "status": STATUS_ERROR, 
                        "message": f"API 속도 제한(Rate Limit) 오류: {max_retries}회 시도 후 실패했습니다. 잠시 후 다시 시도해주세요.",
                        "retry_after": 60  # 사용자에게 60초 후에 다시 시도하라고 제안
                    }
            
            # API 오류 처리 - 서버 오류
            elif any(x in error_str for x in ['500', '502', '503', '504', 'server error', 'timeout']):
                error_msg = LOG_API_ERROR.format(e)
                logger.error(error_msg)
                logger.debug(traceback.format_exc())
                
                if attempt < max_retries - 1:  # 마지막 시도가 아니면 대기 후 재시도
                    wait_time = base_delay * (2 ** attempt)
                    logger.info(f"API 서버 오류, {wait_time}초 후 재시도합니다. (시도 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:  # 마지막 시도면 실패 반환
                    return {"status": STATUS_ERROR, "message": ERROR_API.format(e)}
            
            # 기타 API 오류
            else:
                error_msg = LOG_API_ERROR.format(e)
                logger.error(error_msg)
                logger.debug(traceback.format_exc())
                return {"status": STATUS_ERROR, "message": ERROR_API.format(e)}

# --- 도구 스키마 정의 ---
from .configs import DEFAULT_PROMPT_TEMPLATE, LOG_VALIDATION_SUCCESS, LOG_SCHEMA_FUNCTION_MISSING, LOG_FUNCTION_NOT_CALLABLE

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "summarize_text",
            "description": "주어진 텍스트를 AI 모델을 사용하여 한국어 한 문장으로 간결하게 요약합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text_to_summarize": {
                        "type": "string",
                        "description": "요약이 필요한 텍스트 내용."
                    },
                     "prompt_template": {
                        "type": "string",
                        "description": "요약 스타일을 지정하는 선택적 프롬프트 템플릿입니다.",
                        "default": DEFAULT_PROMPT_TEMPLATE
                    }
                },
                "required": ["text_to_summarize"]
            }
        }
    }
]

# 함수 이름을 실제 파이썬 함수에 매핑
TOOL_MAP = {
    "summarize_text": summarize_text,
}

# 도구 인터페이스 검증 함수
def validate_tool_interface() -> None:
    """TOOL_SCHEMAS와 TOOL_MAP이 일치하는지 검증하는 함수"""
    # 스키마에 정의된 모든 함수가 TOOL_MAP에 존재하는지 확인
    schema_function_names = [schema["function"]["name"] for schema in TOOL_SCHEMAS if "function" in schema]
    for name in schema_function_names:
        if name not in TOOL_MAP:
            error_msg = LOG_SCHEMA_FUNCTION_MISSING.format(name)
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    # TOOL_MAP의 모든 함수가 호출 가능한지 확인
    for name, func in TOOL_MAP.items():
        if not callable(func):
            error_msg = LOG_FUNCTION_NOT_CALLABLE.format(name)
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    # TOOL_MAP의 모든 함수가 스키마에 정의되어 있는지 확인
    for name in TOOL_MAP:
        if name not in schema_function_names:
            logger.warning(f"TOOL_MAP에 정의된 함수 '{name}'이 스키마에 존재하지 않습니다.")
    
    logger.info(LOG_VALIDATION_SUCCESS)

# 모듈이 로드될 때 자동으로 검증 실행
validate_tool_interface()