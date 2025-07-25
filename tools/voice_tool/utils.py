"""
voice_tool/utils.py - 음성 변환 도구의 유틸리티 함수

이 모듈은 TTS 및 STT 기능을 위한 유틸리티 함수를 제공합니다.
"""

import logging
import speech_recognition as sr
from io import BytesIO
from typing import Optional, Union, Any

from .configs import (
    LOG_STT_ERROR_INVALID,
    MIN_SPEED,
    MAX_SPEED,
    DEFAULT_SPEED
)

# 로거 설정
logger = logging.getLogger(__name__)

def validate_speed(speed: float) -> float:
    """
    음성 속도 값이 유효한 범위 내에 있는지 확인하고 유효한 값을 반환합니다.
    
    Args:
        speed (float): 검증할 음성 속도 값
        
    Returns:
        float: 유효한 범위 내의 속도 값
    """
    if speed < MIN_SPEED:
        logger.warning(f"속도가 최소값({MIN_SPEED})보다 작습니다. 최소값으로 조정합니다.")
        return MIN_SPEED
    elif speed > MAX_SPEED:
        logger.warning(f"속도가 최대값({MAX_SPEED})보다 큽니다. 최대값으로 조정합니다.")
        return MAX_SPEED
    return speed

def prepare_audio_file_from_mic_data(audio_data: sr.AudioData) -> Optional[BytesIO]:
    """
    마이크에서 캡처된 오디오 데이터를 API 호출에 적합한 형식으로 변환합니다.
    
    Args:
        audio_data (sr.AudioData): speech_recognition 라이브러리의 오디오 데이터 객체
        
    Returns:
        Optional[BytesIO]: 메모리 내 파일 객체 또는 오류 시 None
    """
    if not isinstance(audio_data, sr.AudioData):
        logger.error(LOG_STT_ERROR_INVALID)
        return None
        
    try:
        # AudioData 객체에서 WAV 데이터 가져오기
        wav_data = audio_data.get_wav_data()
        
        # 메모리 내 파일과 유사한 객체 생성
        audio_file = BytesIO(wav_data)
        audio_file.name = "from_mic.wav"  # API는 파일 이름을 요구합니다
        
        return audio_file
    except Exception as e:
        logger.error(f"오디오 데이터 준비 중 오류 발생: {e}")
        return None
