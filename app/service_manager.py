#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
서비스 관리 모듈

AI 서비스, 도구, 에이전트 등을 관리하고 조율합니다.
"""

import streamlit as st
from typing import Dict, Any, Optional, List
import logging
import time
from datetime import datetime

from .types import AIResponse, ProcessStatus, ToolResult, ServiceConfig
import assistant_core
from config import config
from logging_config import setup_logging, get_logger

logger = logging.getLogger(__name__)

class ServiceManager:
    """서비스 관리 클래스"""
    
    def __init__(self, session_manager) -> None:
        """ServiceManager 초기화"""
        self.session_manager = session_manager
        self._setup_services()
        self._validate_config()
        logger.info("ServiceManager 초기화 완료")
    
    def _setup_services(self) -> None:
        """서비스 설정"""
        # 로깅 설정
        setup_logging(log_level=config.LOG_LEVEL, log_dir=config.LOG_DIR)
        
        # 필수 환경 변수 검증
        try:
            config.validate_required_keys()
            logger.info("환경 변수 검증 완료")
        except ValueError as e:
            logger.error(f"환경 변수 오류: {e}")
            st.error(f"환경 변수 설정 오류: {e}")
            st.stop()
    
    def _validate_config(self) -> None:
        """설정 검증"""
        if not config.OPENAI_API_KEY:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다")
        
        logger.info("설정 검증 완료")
    
    def process_user_input(self, text_input: str) -> AIResponse:
        """사용자 입력 처리"""
        if not text_input.strip():
            return {
                "status": "error",
                "message": "내용이 없는 메시지는 처리할 수 없습니다."
            }
        
        try:
            # 진행 상황 업데이트
            self._update_process_status("LLM 입력 분석 중...", 0.1)
            
            # 대화 히스토리 준비
            self._update_process_status("대화 이력 준비 중...", 0.3)
            conversation_history = self.session_manager.get_conversation_history()
            
            # 파일 컨텍스트 준비
            file_context = None
            uploaded_file = self.session_manager.get_uploaded_file()
            if uploaded_file:
                file_context = {"uploaded_file": uploaded_file}
            
            # LLM 응답 처리
            self._update_process_status("LLM 응답 대기 중...", 0.5)
            response = assistant_core.process_command_with_llm_and_tools(
                text_input, 
                conversation_history
            )
            
            # 응답 처리
            self._update_process_status("LLM 응답 처리 중...", 0.8)
            processed_response = self._process_ai_response(response)
            
            # 완료
            self._update_process_status("완료", 1.0)
            
            return processed_response
            
        except Exception as e:
            logger.error(f"사용자 입력 처리 중 오류: {e}")
            return {
                "status": "error",
                "message": f"처리 중 오류가 발생했습니다: {str(e)}"
            }
        finally:
            # 프로세스 상태 초기화
            self.session_manager.set_current_process(None)
    
    def _update_process_status(self, desc: str, progress: float) -> None:
        """프로세스 상태 업데이트"""
        process_status: ProcessStatus = {
            "type": "llm",
            "desc": desc,
            "progress": progress
        }
        self.session_manager.set_current_process(process_status)
    
    def _process_ai_response(self, response: Dict[str, Any]) -> AIResponse:
        """AI 응답 처리"""
        if response.get("status") == "success":
            # 응답 타입 확인
            if response.get("response_type") == "audio_response":
                # 음성 및 상세 텍스트 처리
                voice_text = response.get("voice_text", "")
                detailed_text = response.get("detailed_text", "")
                audio_content = response.get("audio_content")
                
                # 세션에 메시지 추가
                self.session_manager.add_assistant_message(
                    content=detailed_text,
                    voice_text=voice_text,
                    detailed_text=detailed_text
                )
                
                return {
                    "status": "success",
                    "response_type": "audio_response",
                    "voice_text": voice_text,
                    "detailed_text": detailed_text,
                    "audio_content": audio_content,
                    "text_content": detailed_text
                }
            
            elif response.get("response_type") == "text_fallback":
                # 텍스트 폴백 응답
                text_content = response.get("text_content", "")
                
                # 세션에 메시지 추가
                self.session_manager.add_assistant_message(content=text_content)
                
                return {
                    "status": "success",
                    "response_type": "text_fallback",
                    "text_content": text_content
                }
            
            else:
                # 일반 텍스트 응답
                message = response.get("message", "") or response.get("response", "")
                
                # 세션에 메시지 추가
                self.session_manager.add_assistant_message(content=message)
                
                return {
                    "status": "success",
                    "text_content": message
                }
        else:
            # 오류 응답
            error_msg = response.get("message", "") or response.get("response", "처리 중 알 수 없는 오류가 발생했습니다.")
            return {
                "status": "error",
                "message": error_msg
            }
    
    def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """도구 실행"""
        start_time = time.time()
        
        try:
            # 도구 실행 로직
            result = self._execute_tool_internal(tool_name, **kwargs)
            
            execution_time = time.time() - start_time
            
            return {
                "success": True,
                "data": result,
                "error": None,
                "execution_time": execution_time
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"도구 실행 실패: {tool_name} - {e}")
            
            return {
                "success": False,
                "data": None,
                "error": str(e),
                "execution_time": execution_time
            }
    
    def _execute_tool_internal(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """내부 도구 실행"""
        # 실제 도구 실행 로직은 여기에 구현
        # 현재는 기본적인 구조만 제공
        logger.info(f"도구 실행: {tool_name} with {kwargs}")
        
        # 예시: 기획서 작성 도구
        if tool_name == "create_planning_document":
            from tools.planning_tool.core import execute_create_new_planning_document
            return execute_create_new_planning_document(**kwargs)
        
        # 예시: 이메일 요약 도구
        elif tool_name == "get_email_summary":
            from tools.email_tool import get_daily_email_summary
            return get_daily_email_summary(**kwargs)
        
        else:
            raise ValueError(f"알 수 없는 도구: {tool_name}")
    
    def get_service_status(self) -> Dict[str, Any]:
        """서비스 상태 반환"""
        return {
            "openai_api_available": bool(config.OPENAI_API_KEY),
            "notion_api_available": bool(config.NOTION_API_KEY),
            "gmail_api_available": bool(config.GMAIL_ADDRESS and config.GMAIL_APP_PASSWORD),
            "log_level": config.LOG_LEVEL,
            "environment": "development" if config.is_development() else "production"
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 반환"""
        # 실제 구현에서는 더 상세한 메트릭을 수집할 수 있음
        return {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0,
            "uptime": time.time(),
            "memory_usage": 0.0
        }
    
    def validate_service_config(self) -> bool:
        """서비스 설정 검증"""
        try:
            # OpenAI API 키 검증
            if not config.OPENAI_API_KEY:
                logger.error("OpenAI API 키가 설정되지 않았습니다")
                return False
            
            # 선택적 API 키들 검증
            if config.NOTION_API_KEY and not config.NOTION_PARENT_PAGE_ID:
                logger.warning("Notion API 키는 있지만 부모 페이지 ID가 설정되지 않았습니다")
            
            if config.GMAIL_ADDRESS and not config.GMAIL_APP_PASSWORD:
                logger.warning("Gmail 주소는 있지만 앱 비밀번호가 설정되지 않았습니다")
            
            logger.info("서비스 설정 검증 완료")
            return True
            
        except Exception as e:
            logger.error(f"서비스 설정 검증 실패: {e}")
            return False
    
    def cleanup(self) -> None:
        """서비스 관리자 정리"""
        logger.info("ServiceManager 정리 완료")
    
    def get_available_tools(self) -> List[str]:
        """사용 가능한 도구 목록 반환"""
        return [
            "create_planning_document",
            "get_email_summary",
            "search_emails",
            "speak_text",
            "summarize_text"
        ]
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """도구 정보 반환"""
        tool_info = {
            "create_planning_document": {
                "name": "기획서 작성",
                "description": "AI 기반 기획서 자동 생성",
                "parameters": ["user_input", "writer_persona", "reviewer_persona", "template_name"]
            },
            "get_email_summary": {
                "name": "이메일 요약",
                "description": "일일 이메일 요약 생성",
                "parameters": ["days_ago", "mail_folder", "max_results"]
            },
            "search_emails": {
                "name": "이메일 검색",
                "description": "이메일 검색 및 필터링",
                "parameters": ["keywords", "subject", "date_range"]
            },
            "speak_text": {
                "name": "음성 합성",
                "description": "텍스트를 음성으로 변환",
                "parameters": ["text", "speed"]
            },
            "summarize_text": {
                "name": "텍스트 요약",
                "description": "긴 텍스트를 요약",
                "parameters": ["text", "prompt_template"]
            }
        }
        
        return tool_info.get(tool_name)
    
    def handle_service_error(self, error: Exception, context: str = "") -> AIResponse:
        """서비스 오류 처리"""
        error_message = str(error)
        logger.error(f"서비스 오류 ({context}): {error_message}")
        
        return {
            "status": "error",
            "message": f"서비스 오류가 발생했습니다: {error_message}"
        } 