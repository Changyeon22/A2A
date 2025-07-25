#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
voice_tool 모듈

텍스트-음성 변환(TTS) 및 음성-텍스트 변환(STT) 기능을 제공하는 도구 모듈입니다.

주요 기능:
- 텍스트를 음성으로 변환 (TTS)
- 마이크 음성을 텍스트로 변환 (STT)
- 다양한 언어 및 음성 옵션 지원
- 실시간 음성 인식 및 처리
"""

from .core import (
    speak_text,
    speech_to_text_from_mic_data,
    TOOL_SCHEMAS,
    TOOL_MAP,
    validate_tool_interface
)

__version__ = "1.0.0"
__author__ = "AI Agent System"

# 모듈에서 외부로 노출할 함수들
__all__ = [
    'speak_text',
    'speech_to_text_from_mic_data',
    'TOOL_SCHEMAS',
    'TOOL_MAP',
    'validate_tool_interface'
]
