#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
메인 애플리케이션 모듈

분리된 모듈들을 조율하여 전체 애플리케이션을 실행합니다.
"""

import streamlit as st
import time
from typing import Optional
import logging

from .session_manager import SessionManager
from .ui_manager import UIManager
from .voice_manager import VoiceManager
from .service_manager import ServiceManager
from .types import AIResponse

logger = logging.getLogger(__name__)

class AIAgentApp:
    """AI 에이전트 애플리케이션 메인 클래스"""
    
    def __init__(self) -> None:
        """애플리케이션 초기화"""
        self.session_manager = SessionManager()
        self.ui_manager = UIManager()
        self.voice_manager = VoiceManager(self.session_manager)
        self.service_manager = ServiceManager(self.session_manager)
        
        logger.info("AI Agent 애플리케이션 초기화 완료")
    
    def run(self) -> None:
        """애플리케이션 실행"""
        try:
            # 메인 인터페이스 렌더링
            user_input = self.ui_manager.render_main_interface(self.session_manager)
            
            # 사용자 입력 처리
            if user_input:
                self._process_user_input(user_input)
            
            # 음성 인식 상태 확인 및 처리
            self._handle_voice_recognition()
            
            # 사이드바 렌더링
            self.ui_manager.render_sidebar(self.session_manager)
            
            # 진행 상황 표시
            current_process = self.session_manager.get_current_process()
            if current_process:
                self.ui_manager.render_progress_indicator(current_process)
            
        except Exception as e:
            logger.error(f"애플리케이션 실행 중 오류: {e}")
            self.ui_manager.render_error_message(str(e))
    
    def _process_user_input(self, text_input: str) -> None:
        """사용자 입력 처리"""
        try:
            # 사용자 메시지 추가
            self.session_manager.add_user_message(text_input)
            
            # 서비스를 통한 입력 처리
            response = self.service_manager.process_user_input(text_input)
            
            # 응답 처리
            self._handle_ai_response(response)
            
        except Exception as e:
            logger.error(f"사용자 입력 처리 중 오류: {e}")
            self.ui_manager.render_error_message(str(e))
    
    def _handle_ai_response(self, response: AIResponse) -> None:
        """AI 응답 처리"""
        if response.get("status") == "success":
            if response.get("response_type") == "audio_response":
                # 음성 응답 처리
                self.voice_manager.process_ai_response_audio(response)
                
                # 오디오 재생
                if response.get("audio_content"):
                    self.ui_manager.play_audio_autoplay(response["audio_content"])
            
            else:
                # 텍스트 응답 처리
                text_content = response.get("text_content", "")
                if text_content:
                    self.session_manager.add_assistant_message(content=text_content)
        
        else:
            # 오류 응답 처리
            error_message = response.get("message", "알 수 없는 오류가 발생했습니다.")
            self.ui_manager.render_error_message(error_message)
    
    def _handle_voice_recognition(self) -> None:
        """음성 인식 처리"""
        # 음성 인식 토글 상태 확인 및 처리
        if self.session_manager.is_voice_recognition_active():
            # 토글이 켜져 있으면 음성 인식 스레드 시작
            self.voice_manager.start_continuous_voice_recognition()
        else:
            # 토글이 꺼져 있으면 음성 인식 중지 시도
            voice_thread = self.session_manager.get_voice_thread()
            if voice_thread and voice_thread.is_alive():
                self.voice_manager.stop_continuous_voice_recognition()
    
    def cleanup(self) -> None:
        """애플리케이션 정리"""
        try:
            self.voice_manager.cleanup()
            self.service_manager.cleanup()
            logger.info("애플리케이션 정리 완료")
        except Exception as e:
            logger.error(f"애플리케이션 정리 중 오류: {e}")

def main() -> None:
    """메인 함수"""
    logger.info("AI Agent 애플리케이션 시작")
    
    # 캐시 무효화를 위한 타임스탬프 기록
    _cache_invalidation_time = time.time()
    
    # 브라우저에 직접 스크립트 삽입
    st.markdown("""
    <script>
    // 브라우저 캐시 강제 초기화
    if (window.localStorage) {
        // 마지막 초기화 시간 확인
        const lastReset = localStorage.getItem('streamlit_cache_reset');
        const now = Date.now();
        
        // 1시간마다 캐시 초기화 (3600000 밀리초)
        if (!lastReset || (now - parseInt(lastReset)) > 3600000) {
            console.log('Forcing cache reset...');
            localStorage.clear();
            sessionStorage.clear();
            localStorage.setItem('streamlit_cache_reset', now.toString());
            // 화면 새로고침
            setTimeout(() => { location.reload(true); }, 100);
        }
    }
    </script>
    """, unsafe_allow_html=True)
    
    # 애플리케이션 인스턴스 생성 및 실행
    app = AIAgentApp()
    
    try:
        app.run()
    except Exception as e:
        logger.error(f"애플리케이션 실행 중 치명적 오류: {e}")
        st.error(f"애플리케이션 오류: {e}")
    finally:
        app.cleanup()

if __name__ == "__main__":
    main() 