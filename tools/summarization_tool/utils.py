"""
요약 도구 모듈의 유틸리티 함수

이 모듈은 summarization_tool에서 사용되는 유틸리티 함수들을 제공합니다.
"""

from typing import Dict, Any
import logging
from .configs import MAX_TEXT_LENGTH, LOG_PROMPT_READY

# 로거 설정
logger = logging.getLogger(__name__)

def prepare_text_for_summarization(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """
    요약을 위해 텍스트를 준비합니다. 최대 길이를 초과하는 텍스트는 잘라냅니다.

    Args:
        text (str): 준비할 원본 텍스트
        max_length (int): 최대 허용 길이

    Returns:
        str: 처리된 텍스트
    """
    # 앞뒤 공백 제거
    cleaned_text = text.strip()
    
    # 텍스트 길이 제한
    truncated_text = cleaned_text[:max_length]
    return truncated_text

def create_summary_prompt(text: str, prompt_template: str) -> str:
    """
    요약 프롬프트를 생성합니다.

    Args:
        text (str): 요약할 텍스트
        prompt_template (str): 프롬프트 템플릿

    Returns:
        str: 완성된 프롬프트
    """
    full_prompt = f"{prompt_template}\n\n---\n{text}\n---"
    logger.debug(LOG_PROMPT_READY.format(len(full_prompt)))
    return full_prompt
