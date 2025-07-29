#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
세션 상태 관리 모듈

Streamlit 세션 상태를 관리하고 초기화하는 기능을 제공합니다.
"""

import streamlit as st
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from .types import (
    Message, SessionState, ProcessStatus, UploadedFile,
    dict_to_message, is_valid_session_state
)

logger = logging.getLogger(__name__)

class SessionManager:
    """세션 상태 관리 클래스"""
    
    def __init__(self) -> None:
        """SessionManager 초기화"""
        self._initialize_session_state()
        logger.info("SessionManager 초기화 완료")
    
    def _initialize_session_state(self) -> None:
        """세션 상태 초기화"""
        # 메시지 히스토리 초기화
        if "messages" not in st.session_state:
            st.session_state.messages = []
            # 시스템 프롬프트 추가
            system_prompt = """You are an expert AI Planning Assistant. Your primary goal is to help users develop comprehensive and actionable plans for various projects, with a special focus on game development and IT projects.

Key Responsibilities:
- Analyze user requests to understand their planning needs.
- Break down complex goals into manageable tasks and phases.
- Help define project scope, objectives, deliverables, and timelines.
- Identify potential risks and suggest mitigation strategies.
- Utilize available tools to create, modify, or retrieve planning documents (e.g., from Notion).
- Maintain a professional, clear, and helpful tone.
- If a user's request is ambiguous or lacks detail, ask clarifying questions to ensure a thorough understanding before proceeding.
- When providing plans or analysis, aim for clarity, conciseness, and actionable insights.
- Explain your reasoning step-by-step if the query is complex or if you are about to use a tool.

Constraints:
- Only use the provided tools when necessary and appropriate for the user's request.
- Do not make up information if it's not available through tools or your general knowledge.
- Adhere to the structure and format requested by the user for any documents or plans.
- All outputs should be in Korean unless explicitly requested otherwise by the user."""
            
            st.session_state.messages.append({
                "role": "system", 
                "content": system_prompt,
                "timestamp": datetime.now()
            })
            
            # 초기 인사말 추가
            st.session_state.messages.append({
                "role": "assistant", 
                "content": "안녕하세요! AI 기획 비서입니다. 무엇을 도와드릴까요?",
                "timestamp": datetime.now()
            })
        
        # 텍스트 입력 초기화
        if "text_input" not in st.session_state:
            st.session_state.text_input = ""
        
        # 음성 인식 상태 초기화
        if "voice_recognition_active" not in st.session_state:
            st.session_state.voice_recognition_active = False
        
        # 초기 인사말 재생 상태 초기화
        if "initial_greeting_played" not in st.session_state:
            st.session_state.initial_greeting_played = False
        
        # 현재 프로세스 상태 초기화
        if "current_process" not in st.session_state:
            st.session_state.current_process = None
        
        # 업로드된 파일 초기화
        if "chatbot_uploaded_file" not in st.session_state:
            st.session_state.chatbot_uploaded_file = None
        
        # 음성 스레드 초기화
        if "voice_thread" not in st.session_state:
            st.session_state.voice_thread = None
        
        # 음성 상태 플레이스홀더 초기화
        if "voice_status_placeholder" not in st.session_state:
            st.session_state.voice_status_placeholder = None
    
    def get_session_state(self) -> SessionState:
        """현재 세션 상태를 반환"""
        return {
            "messages": st.session_state.get("messages", []),
            "text_input": st.session_state.get("text_input", ""),
            "voice_recognition_active": st.session_state.get("voice_recognition_active", False),
            "initial_greeting_played": st.session_state.get("initial_greeting_played", False),
            "current_process": st.session_state.get("current_process"),
            "chatbot_uploaded_file": st.session_state.get("chatbot_uploaded_file")
        }
    
    def add_message(self, message: Message) -> None:
        """메시지를 세션에 추가"""
        if not is_valid_message(message):
            logger.warning(f"유효하지 않은 메시지 형식: {message}")
            return
        
        st.session_state.messages.append(message)
        logger.debug(f"메시지 추가됨: {message.get('role')} - {message.get('content', '')[:50]}...")
    
    def add_user_message(self, content: str) -> None:
        """사용자 메시지 추가"""
        message: Message = {
            "role": "user",
            "content": content,
            "voice_text": None,
            "detailed_text": None,
            "timestamp": datetime.now()
        }
        self.add_message(message)
    
    def add_assistant_message(self, content: str, voice_text: Optional[str] = None, 
                            detailed_text: Optional[str] = None) -> None:
        """어시스턴트 메시지 추가"""
        message: Message = {
            "role": "assistant",
            "content": content,
            "voice_text": voice_text,
            "detailed_text": detailed_text,
            "timestamp": datetime.now()
        }
        self.add_message(message)
    
    def get_messages(self) -> List[Message]:
        """모든 메시지 반환"""
        return st.session_state.get("messages", [])
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """LLM용 대화 히스토리 반환"""
        conversation_history = []
        for msg in st.session_state.get("messages", []):
            if msg["role"] in ["user", "assistant"]:
                if "voice_text" in msg and "detailed_text" in msg:
                    conversation_history.append({
                        "role": msg["role"], 
                        "content": msg["detailed_text"]
                    })
                elif "content" in msg:
                    conversation_history.append({
                        "role": msg["role"], 
                        "content": msg["content"]
                    })
        return conversation_history
    
    def set_text_input(self, text: str) -> None:
        """텍스트 입력 설정"""
        st.session_state.text_input = text
    
    def get_text_input(self) -> str:
        """텍스트 입력 반환"""
        return st.session_state.get("text_input", "")
    
    def set_voice_recognition_active(self, active: bool) -> None:
        """음성 인식 활성화 상태 설정"""
        st.session_state.voice_recognition_active = active
        logger.info(f"음성 인식 상태 변경: {active}")
    
    def is_voice_recognition_active(self) -> bool:
        """음성 인식 활성화 상태 확인"""
        return st.session_state.get("voice_recognition_active", False)
    
    def set_initial_greeting_played(self, played: bool) -> None:
        """초기 인사말 재생 상태 설정"""
        st.session_state.initial_greeting_played = played
    
    def is_initial_greeting_played(self) -> bool:
        """초기 인사말 재생 상태 확인"""
        return st.session_state.get("initial_greeting_played", False)
    
    def set_current_process(self, process: Optional[ProcessStatus]) -> None:
        """현재 프로세스 상태 설정"""
        st.session_state.current_process = process
    
    def get_current_process(self) -> Optional[ProcessStatus]:
        """현재 프로세스 상태 반환"""
        return st.session_state.get("current_process")
    
    def set_uploaded_file(self, file: Optional[UploadedFile]) -> None:
        """업로드된 파일 설정"""
        st.session_state.chatbot_uploaded_file = file
    
    def get_uploaded_file(self) -> Optional[UploadedFile]:
        """업로드된 파일 반환"""
        return st.session_state.get("chatbot_uploaded_file")
    
    def set_voice_thread(self, thread) -> None:
        """음성 스레드 설정"""
        st.session_state.voice_thread = thread
    
    def get_voice_thread(self):
        """음성 스레드 반환"""
        return st.session_state.get("voice_thread")
    
    def set_voice_status_placeholder(self, placeholder) -> None:
        """음성 상태 플레이스홀더 설정"""
        st.session_state.voice_status_placeholder = placeholder
    
    def get_voice_status_placeholder(self):
        """음성 상태 플레이스홀더 반환"""
        return st.session_state.get("voice_status_placeholder")
    
    def clear_messages(self) -> None:
        """메시지 히스토리 초기화"""
        st.session_state.messages = []
        logger.info("메시지 히스토리 초기화됨")
    
    def clear_session(self) -> None:
        """세션 상태 완전 초기화"""
        st.session_state.clear()
        self._initialize_session_state()
        logger.info("세션 상태 완전 초기화됨")
    
    def get_session_info(self) -> Dict[str, Any]:
        """세션 정보 반환"""
        return {
            "message_count": len(st.session_state.get("messages", [])),
            "voice_active": st.session_state.get("voice_recognition_active", False),
            "has_uploaded_file": st.session_state.get("chatbot_uploaded_file") is not None,
            "current_process": st.session_state.get("current_process"),
            "initial_greeting_played": st.session_state.get("initial_greeting_played", False)
        }
    
    def validate_session_state(self) -> bool:
        """세션 상태 유효성 검증"""
        try:
            state = self.get_session_state()
            return is_valid_session_state(state)
        except Exception as e:
            logger.error(f"세션 상태 검증 실패: {e}")
            return False 