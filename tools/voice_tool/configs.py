"""
voice_tool/configs.py - 음성 변환 도구의 설정 및 상수

이 모듈은 voice_tool에서 사용되는 모든 상수, 기본값 및 메시지를 정의합니다.
"""

import logging

# 로거 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# TTS(Text-to-Speech) 설정
DEFAULT_TTS_MODEL = "tts-1-hd"  # 고품질 모델
DEFAULT_TTS_VOICE = "shimmer"   # 기본 음성
DEFAULT_SPEED = 1.0             # 기본 음성 속도
MIN_SPEED = 0.25                # 최소 음성 속도
MAX_SPEED = 4.0                 # 최대 음성 속도

# STT(Speech-to-Text) 설정
DEFAULT_STT_MODEL = "whisper-1"  # 기본 STT 모델
DEFAULT_LANGUAGE = "ko"          # 기본 언어 (한국어)

# 상태 및 오류 메시지
STATUS_SUCCESS = "success"
STATUS_ERROR = "error"

# 로그 메시지
LOG_TTS_START = "[voice_tool] TTS 변환 시도: '{}'"
LOG_TTS_ERROR_EMPTY = "[voice_tool] TTS 오류: 텍스트가 제공되지 않았습니다."
LOG_TTS_SUCCESS = "[voice_tool] TTS 변환 성공: {} bytes"
LOG_TTS_ERROR = "[voice_tool] OpenAI TTS API 호출 오류: {}"

LOG_STT_ERROR_INVALID = "[voice_tool] STT 오류: 잘못된 오디오 데이터가 제공되었습니다."
LOG_STT_SUCCESS = "[voice_tool] STT 변환 성공: '{}'"
LOG_STT_ERROR = "[voice_tool] OpenAI Whisper API 호출 오류: {}"

# 도구 설명
TOOL_DESCRIPTION_SPEAK_TEXT = "사용자에게 전달할 텍스트를 음성으로 변환하여 말합니다. 대화의 최종 응답을 전달할 때 반드시 사용해야 합니다. 상황과 어조에 맞게 속도를 조절할 수 있습니다."
PARAM_DESC_TEXT = "사용자에게 말할 내용."
PARAM_DESC_SPEED = f"음성의 속도. {MIN_SPEED}(매우 느림)부터 {MAX_SPEED}(매우 빠름)까지 설정 가능합니다. 기본값: {DEFAULT_SPEED}"
