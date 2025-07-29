#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
타입 정의 모듈

애플리케이션에서 사용되는 모든 타입 정의를 포함합니다.
"""

from typing import Dict, Any, Optional, List, Union, TypedDict, Literal
from dataclasses import dataclass
from datetime import datetime
import streamlit as st

# 메시지 타입 정의
class Message(TypedDict):
    role: Literal["user", "assistant", "system"]
    content: str
    voice_text: Optional[str]
    detailed_text: Optional[str]
    timestamp: Optional[datetime]

# 응답 타입 정의
class AIResponse(TypedDict):
    status: Literal["success", "error"]
    message: Optional[str]
    audio_content: Optional[bytes]
    text_content: Optional[str]
    response_type: Optional[Literal["audio_response", "text_fallback"]]
    voice_text: Optional[str]
    detailed_text: Optional[str]

# 진행 상황 타입 정의
class ProcessStatus(TypedDict):
    type: Literal["llm", "prompt", "voice", "email"]
    desc: str
    progress: float

# 파일 업로드 타입 정의
class UploadedFile(TypedDict):
    name: str
    type: str
    data: bytes
    size: int

# 음성 인식 설정 타입 정의
class VoiceConfig(TypedDict):
    language: str
    timeout: float
    phrase_time_limit: float
    continuous: bool

# 에이전트 메시지 타입 정의
class AgentMessage(TypedDict):
    sender_id: str
    receiver_id: str
    message_type: str
    content: Dict[str, Any]
    timestamp: datetime

# 도구 실행 결과 타입 정의
class ToolResult(TypedDict):
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    execution_time: float

# 세션 상태 타입 정의
class SessionState(TypedDict):
    messages: List[Message]
    text_input: str
    voice_recognition_active: bool
    initial_greeting_played: bool
    current_process: Optional[ProcessStatus]
    chatbot_uploaded_file: Optional[UploadedFile]

# UI 컴포넌트 타입 정의
class UIComponent(TypedDict):
    type: Literal["chat", "voice", "settings", "tools"]
    visible: bool
    data: Dict[str, Any]

# 서비스 설정 타입 정의
class ServiceConfig(TypedDict):
    openai_api_key: str
    notion_api_key: Optional[str]
    gmail_address: Optional[str]
    gmail_app_password: Optional[str]
    log_level: str
    log_dir: str

# 성능 메트릭 타입 정의
@dataclass
class PerformanceMetric:
    function_name: str
    execution_time: float
    memory_usage: float
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None

# 캐시 데이터 타입 정의
class CacheData(TypedDict):
    key: str
    value: Any
    timestamp: datetime
    ttl: int

# 로그 엔트리 타입 정의
class LogEntry(TypedDict):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    message: str
    timestamp: datetime
    module: str
    function: str
    line_number: int
    extra_data: Optional[Dict[str, Any]]

# 에러 정보 타입 정의
class ErrorInfo(TypedDict):
    error_type: str
    message: str
    stack_trace: Optional[str]
    context: Dict[str, Any]
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# 설정 검증 결과 타입 정의
class ValidationResult(TypedDict):
    is_valid: bool
    missing_keys: List[str]
    invalid_values: List[str]
    warnings: List[str]

# 타입 유틸리티 함수들
def is_valid_message(message: Dict[str, Any]) -> bool:
    """메시지가 유효한 형식인지 확인"""
    required_keys = {"role", "content"}
    return all(key in message for key in required_keys)

def is_valid_response(response: Dict[str, Any]) -> bool:
    """응답이 유효한 형식인지 확인"""
    required_keys = {"status"}
    return all(key in response for key in required_keys)

def is_valid_session_state(state: Dict[str, Any]) -> bool:
    """세션 상태가 유효한 형식인지 확인"""
    required_keys = {"messages"}
    return all(key in state for key in required_keys)

# 타입 변환 함수들
def dict_to_message(data: Dict[str, Any]) -> Message:
    """딕셔너리를 Message 타입으로 변환"""
    return Message(
        role=data.get("role", "user"),
        content=data.get("content", ""),
        voice_text=data.get("voice_text"),
        detailed_text=data.get("detailed_text"),
        timestamp=data.get("timestamp")
    )

def dict_to_response(data: Dict[str, Any]) -> AIResponse:
    """딕셔너리를 AIResponse 타입으로 변환"""
    return AIResponse(
        status=data.get("status", "error"),
        message=data.get("message"),
        audio_content=data.get("audio_content"),
        text_content=data.get("text_content"),
        response_type=data.get("response_type"),
        voice_text=data.get("voice_text"),
        detailed_text=data.get("detailed_text")
    )

# 타입 가드 함수들
def is_audio_response(response: Dict[str, Any]) -> bool:
    """응답이 음성 응답인지 확인"""
    return response.get("response_type") == "audio_response"

def is_text_response(response: Dict[str, Any]) -> bool:
    """응답이 텍스트 응답인지 확인"""
    return response.get("response_type") == "text_fallback"

def is_error_response(response: Dict[str, Any]) -> bool:
    """응답이 오류 응답인지 확인"""
    return response.get("status") == "error"

# 유니온 타입 정의
ResponseType = Union[AIResponse, Dict[str, Any]]
MessageType = Union[Message, Dict[str, Any]]
StateType = Union[SessionState, Dict[str, Any]] 