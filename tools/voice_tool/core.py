"""
voice_tool/core.py - 음성 변환 관련 도구 모듈

이 모듈은 텍스트-음성 변환(TTS) 및 음성-텍스트 변환(STT) 기능을 제공합니다.
OpenAI의 TTS API와 Whisper API를 활용하여 구현되었습니다.

주요 기능:
1. speak_text: LLM이 호출하는 텍스트-음성 변환 도구
2. speech_to_text_from_mic_data: 마이크 입력을 텍스트로 변환하는 유틸리티 함수
"""

import sys
import os
import logging
import traceback
import openai
from openai import OpenAI
import speech_recognition as sr
from typing import Dict, List, Optional, Union, Any

# 상위 디렉토리 import를 위한 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from tool_interface import ToolInterface
except ImportError:
    # 개발 시 tool_interface.py가 없을 수 있으므로 대비
    class ToolInterface:
        pass

# 로컬 모듈 import
from .configs import (
    DEFAULT_TTS_MODEL,
    DEFAULT_TTS_VOICE,
    DEFAULT_SPEED,
    DEFAULT_STT_MODEL,
    DEFAULT_LANGUAGE,
    STATUS_SUCCESS,
    STATUS_ERROR,
    LOG_TTS_START,
    LOG_TTS_ERROR_EMPTY,
    LOG_TTS_SUCCESS,
    LOG_TTS_ERROR,
    LOG_STT_ERROR_INVALID,
    LOG_STT_SUCCESS,
    LOG_STT_ERROR,
    TOOL_DESCRIPTION_SPEAK_TEXT,
    PARAM_DESC_TEXT,
    PARAM_DESC_SPEED
)
from .utils import validate_speed, prepare_audio_file_from_mic_data

# 로거 설정
logger = logging.getLogger(__name__)

# --- LLM이 사용할 도구 명세 (TOOL_SCHEMAS) ---
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "speak_text",
            "description": TOOL_DESCRIPTION_SPEAK_TEXT,
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": PARAM_DESC_TEXT
                    },
                    "detailed_text": {
                        "type": "string",
                        "description": "상세 답변 텍스트. UI에 표시될 상세한 내용으로, 음성으로는 전달되지 않음."
                    },
                    "speed": {
                        "type": "number",
                        "description": PARAM_DESC_SPEED
                    }
                },
                "required": ["text"]
            }
        }
    }
]

def speak_text(text: str, detailed_text: str = "", speed: float = DEFAULT_SPEED) -> Optional[bytes]:
    """
    OpenAI의 TTS API를 사용하여 텍스트를 음성으로 변환합니다.
    
    LLM이 직접 호출하는 '도구'로, 사용자에게 음성 응답을 전달하는 데 사용됩니다.
    대화의 최종 응답을 전달할 때 반드시 사용해야 합니다.
    
    Args:
        text (str): 음성으로 변환할 텍스트. 필수 파라미터.
        speed (float, optional): 음성 재생 속도. 기본값 1.0.
                               범위는 0.25(매우 느림)~4.0(매우 빠름).
    
    Returns:
        Optional[bytes]: 생성된 오디오 데이터의 바이트, 오류 시 None.
    
    Raises:
        Exception: OpenAI API 호출 중 발생한 예외는 내부적으로 처리되고 로그에 기록됨.
    """
    logger.info(LOG_TTS_START.format(text))
    
    if not text or not text.strip():
        logger.warning(LOG_TTS_ERROR_EMPTY)
        return None
    
    # 속도 값 검증
    validated_speed = validate_speed(speed)
    
    try:
        # OpenAI 클라이언트 초기화 - 함수 내부에서 호출할 때마다 생성
        client = OpenAI()
        
        response = client.audio.speech.create(
            model=DEFAULT_TTS_MODEL,
            voice=DEFAULT_TTS_VOICE,
            input=text,
            speed=validated_speed
        )
        audio_bytes = response.content
        logger.info(LOG_TTS_SUCCESS.format(len(audio_bytes)))
        
        # 내부적으로는 성공 상태를 기록하지만, 외부로는 기존 호환성을 위해 바이트 반환
        return audio_bytes
    except Exception as e:
        error_msg = LOG_TTS_ERROR.format(str(e))
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return None

# --- 도구 이름과 실제 함수를 매핑 (TOOL_MAP) ---
TOOL_MAP = {
    "speak_text": speak_text,
}

# 도구 인터페이스 검증 함수
def validate_tool_interface() -> bool:
    """
    TOOL_SCHEMAS와 TOOL_MAP이 일치하는지 검증합니다.
    
    Returns:
        bool: 검증 성공 시 True, 실패 시 False
    """
    schema_names = set()
    for schema in TOOL_SCHEMAS:
        if schema.get("type") == "function" and "function" in schema:
            schema_names.add(schema["function"]["name"])
    
    map_names = set(TOOL_MAP.keys())
    
    if schema_names != map_names:
        missing_in_schema = map_names - schema_names
        missing_in_map = schema_names - map_names
        
        if missing_in_schema:
            logger.error(f"TOOL_MAP에는 있지만 TOOL_SCHEMAS에는 없는 함수: {missing_in_schema}")
        
        if missing_in_map:
            logger.error(f"TOOL_SCHEMAS에는 있지만 TOOL_MAP에는 없는 함수: {missing_in_map}")
        
        return False
    
    logger.info(f"voice_tool 인터페이스 검증 성공: {len(schema_names)}개 함수 확인")
    return True

# 모듈 로드 시 자동 검증 실행
_ = validate_tool_interface()

# ====================================================================
# 아래 함수는 LLM이 사용하는 도구가 아닌, app.py에서 사용하는 유틸리티입니다.
# ====================================================================


def speech_to_text_from_mic_data(audio_data: sr.AudioData) -> Dict[str, Any]:
    """
    마이크에서 캡처된 오디오 데이터를 OpenAI의 Whisper API를 사용하여 텍스트로 변환합니다.
    
    이 함수는 app.py에서 사용하는 유틸리티 함수로, LLM이 직접 호출하지 않습니다.
    
    Args:
        audio_data (sr.AudioData): speech_recognition 라이브러리의 오디오 데이터 객체.
                                  마이크 입력으로부터 생성됩니다.
    
    Returns:
        Dict[str, Any]: 상태와 변환된 텍스트 또는 오류 메시지를 포함하는 딕셔너리.
    
    Raises:
        Exception: OpenAI API 호출 중 발생한 예외는 내부적으로 처리되고 로그에 기록됨.
    """
    # 오디오 데이터 검증
    audio_file = prepare_audio_file_from_mic_data(audio_data)
    if not audio_file:
        return {"status": STATUS_ERROR, "message": LOG_STT_ERROR_INVALID}

    try:
        # OpenAI 클라이언트 초기화 - 함수 내부에서 호출할 때마다 생성
        client = OpenAI()
        
        # Whisper API 호출
        transcription = client.audio.transcriptions.create(
            model=DEFAULT_STT_MODEL,
            file=audio_file,
            language=DEFAULT_LANGUAGE
        )
        
        result_text = transcription.text
        logger.info(LOG_STT_SUCCESS.format(result_text))
        
        return {
            "status": STATUS_SUCCESS,
            "text": result_text
        }
    except Exception as e:
        error_msg = LOG_STT_ERROR.format(str(e))
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return {"status": STATUS_ERROR, "message": error_msg}
