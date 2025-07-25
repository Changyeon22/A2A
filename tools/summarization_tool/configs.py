"""
요약 도구 모듈의 설정 및 상수 정의

이 모듈은 summarization_tool에서 사용되는 모든 상수, 기본값 및 메시지를 정의합니다.
"""

import os
import logging

# 로거 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# OpenAI 모델 설정
DEFAULT_MODEL = "gpt-4o"
DEFAULT_MAX_TOKENS = 2000
DEFAULT_TEMPERATURE = 0.5

# 요약 설정
DEFAULT_PROMPT_TEMPLATE = "다음 텍스트를 한국어 한 문장으로 간결하게 요약해줘:"
MAX_TEXT_LENGTH = 40000  # 비용 및 성능 관리를 위한 텍스트 길이 제한

# 시스템 메시지
SYSTEM_MESSAGE = "You are a helpful assistant specialized in summarizing text concisely in Korean."

# 상태 및 오류 메시지
STATUS_SUCCESS = "success"
STATUS_ERROR = "error"

ERROR_EMPTY_TEXT = "비어있는 텍스트입니다. 입력된 텍스트가 없습니다."
ERROR_API = "OpenAI API 오류: {}"
ERROR_UNEXPECTED = "예상치 못한 오류 발생: {}"

# 로그 메시지
LOG_START = "텍스트 요약 작업 시작"
LOG_EMPTY_TEXT = "빈 텍스트가 입력되었습니다"
LOG_PROMPT_READY = "요약 프롬프트 구성 완료: {} 자"
LOG_API_CALL = "OpenAI API 호출 중..."
LOG_COMPLETE = "텍스트 요약 완료"
LOG_API_ERROR = "OpenAI API error during summarization: {}"
LOG_UNEXPECTED_ERROR = "An unexpected error occurred during summarization: {}"
LOG_VALIDATION_SUCCESS = "summarization_tool 모듈이 표준 인터페이스를 준수합니다."
LOG_SCHEMA_FUNCTION_MISSING = "스키마에 정의된 함수 '{}'이 TOOL_MAP에 존재하지 않습니다."
LOG_FUNCTION_NOT_CALLABLE = "TOOL_MAP의 '{}'에 매핑된 객체가 호출 가능한 함수가 아닙니다."
