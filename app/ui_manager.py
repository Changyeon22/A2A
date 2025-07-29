#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UI 관리 모듈

Streamlit UI 컴포넌트들을 관리하고 렌더링하는 기능을 제공합니다.
"""

import streamlit as st
import base64
from typing import Dict, Any, Optional, List
import logging

from .types import Message, AIResponse, ProcessStatus, UploadedFile
from ui_components.display_helpers import (
    show_message, show_spinner_ui, show_ai_response, 
    show_download_button, show_voice_controls, apply_custom_css,
    play_audio_with_feedback, show_voice_status
)

logger = logging.getLogger(__name__)

class UIManager:
    """UI 관리 클래스"""
    
    def __init__(self) -> None:
        """UIManager 초기화"""
        self._setup_page_config()
        self._apply_custom_css()
        logger.info("UIManager 초기화 완료")
    
    def _setup_page_config(self) -> None:
        """페이지 설정"""
        st.set_page_config(
            page_title="AI 기획 비서", 
            layout="wide", 
            initial_sidebar_state="expanded",
            menu_items={
                'Get Help': None,
                'Report a bug': None,
                'About': None
            }
        )
    
    def _apply_custom_css(self) -> None:
        """커스텀 CSS 적용"""
        apply_custom_css()
    
    def render_header(self) -> None:
        """헤더 렌더링"""
        st.markdown("""
        <div class="main-header">
            <h1>🤖 AI 기획 비서</h1>
            <p>멀티 에이전트 기반 AI 자동화 시스템</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_chat_interface(self, messages: List[Message]) -> None:
        """채팅 인터페이스 렌더링"""
        chat_container = st.container()
        
        with chat_container:
            st.markdown('<div class="chat-container">', unsafe_allow_html=True)
            
            for message in messages:
                if message["role"] == "user":
                    show_message(message["content"], "user")
                elif message["role"] == "assistant":
                    if "voice_text" in message and "detailed_text" in message:
                        show_ai_response(
                            voice_text=message["voice_text"],
                            detailed_text=message["detailed_text"]
                        )
                    else:
                        show_message(message["content"], "assistant")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    def render_input_interface(self, session_manager) -> str:
        """입력 인터페이스 렌더링"""
        input_container = st.container()
        
        with input_container:
            st.markdown('<div class="input-container">', unsafe_allow_html=True)
            
            # 텍스트 입력
            text_input = st.text_area(
                "메시지를 입력하세요",
                value=session_manager.get_text_input(),
                key="text_input",
                height=70,
                placeholder="AI 기획 비서에게 질문하세요..."
            )
            
            # 버튼 행
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("전송", key="send_button"):
                    return text_input
            
            with col2:
                if st.button("음성 질문", key="voice_button"):
                    # 음성 입력 처리
                    return self._handle_voice_input()
            
            with col3:
                if st.button("초기화", key="clear_button"):
                    session_manager.clear_messages()
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        return ""
    
    def _handle_voice_input(self) -> str:
        """음성 입력 처리"""
        # 음성 입력 로직은 VoiceManager에서 처리
        return ""
    
    def render_voice_controls(self, session_manager) -> None:
        """음성 컨트롤 렌더링"""
        show_voice_controls(session_manager.is_voice_recognition_active())
    
    def render_progress_indicator(self, process: Optional[ProcessStatus]) -> None:
        """진행 상황 표시기 렌더링"""
        if process:
            with show_spinner_ui(f"🔄 {process['desc']}"):
                st.progress(process['progress'])
    
    def render_file_upload(self, session_manager) -> None:
        """파일 업로드 렌더링"""
        uploaded_file = st.file_uploader(
            "파일 업로드 (선택사항)",
            type=['txt', 'pdf', 'docx', 'md'],
            key="file_uploader"
        )
        
        if uploaded_file is not None:
            file_data = uploaded_file.read()
            file_info: UploadedFile = {
                "name": uploaded_file.name,
                "type": uploaded_file.type,
                "data": file_data,
                "size": len(file_data)
            }
            session_manager.set_uploaded_file(file_info)
            st.success(f"파일 '{uploaded_file.name}' 업로드 완료")
    
    def render_sidebar(self, session_manager) -> None:
        """사이드바 렌더링"""
        with st.sidebar:
            st.header("⚙️ 설정")
            
            # 세션 정보 표시
            session_info = session_manager.get_session_info()
            st.subheader("📊 세션 정보")
            st.write(f"메시지 수: {session_info['message_count']}")
            st.write(f"음성 인식: {'활성' if session_info['voice_active'] else '비활성'}")
            st.write(f"업로드 파일: {'있음' if session_info['has_uploaded_file'] else '없음'}")
            
            # 도구 패널
            st.subheader("🛠️ 도구")
            
            # 기획서 작성 도구
            if st.button("📝 기획서 작성", key="planning_tool"):
                self._show_planning_tool()
            
            # 이메일 도구
            if st.button("📧 이메일 도구", key="email_tool"):
                self._show_email_tool()
            
            # 프롬프트 자동화 도구
            if st.button("🤖 프롬프트 자동화", key="prompt_tool"):
                self._show_prompt_tool()
    
    def _show_planning_tool(self) -> None:
        """기획서 작성 도구 표시"""
        st.session_state.show_planning_tool = True
    
    def _show_email_tool(self) -> None:
        """이메일 도구 표시"""
        st.session_state.show_email_tool = True
    
    def _show_prompt_tool(self) -> None:
        """프롬프트 자동화 도구 표시"""
        st.session_state.show_prompt_tool = True
    
    def render_audio_player(self, audio_bytes: bytes) -> None:
        """오디오 플레이어 렌더링"""
        if audio_bytes:
            st.audio(audio_bytes, format='audio/mp3')
    
    def play_audio_autoplay(self, audio_bytes: bytes) -> None:
        """자동 재생 오디오 렌더링"""
        if not audio_bytes:
            return
        
        audio_base64 = base64.b64encode(audio_bytes).decode()
        audio_html = f"""
            <audio autoplay style="display:none">
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mpeg">
            </audio>
        """
        st.markdown(audio_html, unsafe_allow_html=True)
    
    def render_error_message(self, error_message: str) -> None:
        """오류 메시지 렌더링"""
        st.error(f"오류: {error_message}")
    
    def render_success_message(self, message: str) -> None:
        """성공 메시지 렌더링"""
        st.success(message)
    
    def render_warning_message(self, message: str) -> None:
        """경고 메시지 렌더링"""
        st.warning(message)
    
    def render_info_message(self, message: str) -> None:
        """정보 메시지 렌더링"""
        st.info(message)
    
    def render_download_button(self, data: bytes, filename: str, mime_type: str) -> None:
        """다운로드 버튼 렌더링"""
        show_download_button(data, filename, mime_type)
    
    def render_voice_status(self, status: str, message: str) -> None:
        """음성 상태 렌더링"""
        st.markdown(
            f'<div class="voice-status-area">{show_voice_status(status, message)}</div>',
            unsafe_allow_html=True
        )
    
    def render_tabs(self) -> str:
        """탭 인터페이스 렌더링"""
        tab1, tab2, tab3, tab4 = st.tabs([
            "💬 채팅", 
            "📝 기획서", 
            "📧 이메일", 
            "🤖 프롬프트"
        ])
        
        active_tab = "chat"
        
        with tab1:
            active_tab = "chat"
        
        with tab2:
            if st.session_state.get("show_planning_tool", False):
                self._render_planning_tab()
                active_tab = "planning"
        
        with tab3:
            if st.session_state.get("show_email_tool", False):
                self._render_email_tab()
                active_tab = "email"
        
        with tab4:
            if st.session_state.get("show_prompt_tool", False):
                self._render_prompt_tab()
                active_tab = "prompt"
        
        return active_tab
    
    def _render_planning_tab(self) -> None:
        """기획서 탭 렌더링"""
        st.subheader("📝 기획서 작성 도구")
        st.write("AI 기반 기획서 자동 생성 도구입니다.")
        
        # 기획서 작성 폼
        with st.form("planning_form"):
            project_title = st.text_input("프로젝트 제목")
            document_type = st.selectbox(
                "문서 유형",
                ["게임 기획서", "웹사이트 기획서", "앱 기획서", "비즈니스 계획서"]
            )
            requirements = st.text_area("요구사항")
            
            if st.form_submit_button("기획서 생성"):
                # 기획서 생성 로직
                pass
    
    def _render_email_tab(self) -> None:
        """이메일 탭 렌더링"""
        st.subheader("📧 이메일 도구")
        st.write("이메일 관리 및 분석 도구입니다.")
        
        # 이메일 도구 폼
        with st.form("email_form"):
            email_action = st.selectbox(
                "이메일 작업",
                ["이메일 요약", "이메일 검색", "이메일 응답 생성"]
            )
            
            if st.form_submit_button("실행"):
                # 이메일 작업 로직
                pass
    
    def _render_prompt_tab(self) -> None:
        """프롬프트 탭 렌더링"""
        st.subheader("🤖 프롬프트 자동화")
        st.write("AI 프롬프트 자동 생성 및 최적화 도구입니다.")
        
        # 프롬프트 도구 폼
        with st.form("prompt_form"):
            prompt_type = st.selectbox(
                "프롬프트 유형",
                ["기획서 작성", "이메일 작성", "코드 생성", "분석 리포트"]
            )
            context = st.text_area("컨텍스트")
            
            if st.form_submit_button("프롬프트 생성"):
                # 프롬프트 생성 로직
                pass
    
    def render_main_interface(self, session_manager) -> str:
        """메인 인터페이스 렌더링"""
        # 헤더 렌더링
        self.render_header()
        
        # 탭 렌더링
        active_tab = self.render_tabs()
        
        # 채팅 인터페이스 렌더링
        if active_tab == "chat":
            self.render_chat_interface(session_manager.get_messages())
            user_input = self.render_input_interface(session_manager)
            
            # 음성 컨트롤 렌더링
            self.render_voice_controls(session_manager)
            
            # 파일 업로드 렌더링
            self.render_file_upload(session_manager)
            
            return user_input
        
        return ""
    
    def render_loading_spinner(self, message: str) -> None:
        """로딩 스피너 렌더링"""
        with show_spinner_ui(message):
            pass
    
    def render_metrics(self, metrics: Dict[str, Any]) -> None:
        """메트릭 렌더링"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("총 메시지", metrics.get("total_messages", 0))
        
        with col2:
            st.metric("음성 인식", metrics.get("voice_recognition", 0))
        
        with col3:
            st.metric("파일 업로드", metrics.get("file_uploads", 0))
        
        with col4:
            st.metric("응답 시간", f"{metrics.get('avg_response_time', 0):.2f}s") 