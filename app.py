#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
My AI Agent - 멀티 에이전트 AI 시스템

음성 인식, 이메일 처리, 기획서 작성 등 다양한 AI 기능을 제공하는 
통합 에이전트 시스템의 메인 Streamlit 애플리케이션입니다.
"""

# CACHE_INVALIDATION_TOKEN: f8a9d2c35e17_20250708_1620
# 위 토큰은 Streamlit 캐시를 강제로 무효화하기 위한 것입니다.

import sys
import os
import base64
import streamlit as st
import speech_recognition as sr
import threading
import time
import datetime
import shutil

# 프로젝트 모듈 임포트를 위한 경로 설정
current_script_dir = os.path.dirname(os.path.abspath(__file__))
if current_script_dir not in sys.path:
    sys.path.insert(0, current_script_dir)

# 하위 모듈 경로 추가
for subdir in ["tools", "ui_components", "agents"]:
    subdir_path = os.path.join(current_script_dir, subdir)
    if subdir_path not in sys.path:
        sys.path.insert(0, subdir_path)

# 설정 및 로깅 초기화
from config import config
from logging_config import setup_logging, get_logger

# --- 세션 상태 초기화 ---
if "messages" not in st.session_state:
    st.session_state.messages = [] # 대화 기록 (UI 표시용)
    # Add System Prompt (this will be included in llm_conversation_history but not directly shown in UI)
    st.session_state.messages.append(
        {"role": "system", "content": """You are an expert AI Planning Assistant. Your primary goal is to help users develop comprehensive and actionable plans for various projects, with a special focus on game development and IT projects.

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
        }
    )
    # 초기 인사말 추가 - 일반 텍스트 메시지로 저장
    st.session_state.messages.append({"role": "assistant", "content": "안녕하세요! AI 기획 비서입니다. 무엇을 도와드릴까요?"})

if "text_input" not in st.session_state:
    st.session_state.text_input = ""

if "voice_recognition_active" not in st.session_state:
    st.session_state.voice_recognition_active = False

if "initial_greeting_played" not in st.session_state:
    st.session_state.initial_greeting_played = False

# 로깅 설정
setup_logging(log_level=config.LOG_LEVEL, log_dir=config.LOG_DIR)
logger = get_logger(__name__)

# 필수 환경 변수 검증
try:
    config.validate_required_keys()
    logger.info("환경 변수 검증 완료")
except ValueError as e:
    logger.error(f"환경 변수 오류: {e}")
    st.error(f"환경 변수 설정 오류: {e}")
    st.stop()

import assistant_core
from ui_components.display_helpers import (
    show_message, show_spinner_ui, show_ai_response, 
    show_download_button, show_voice_controls, apply_custom_css,
    play_audio_with_feedback, show_voice_status
)
from tools.voice_tool.core import speech_to_text_from_mic_data
from tools.planning_tool.core import execute_create_new_planning_document
from tools.planning_tool.core import execute_collaboration_planning
from tools.planning_tool.core import execute_expand_notion_document
from tools.planning_tool.configs import personas, DOCUMENT_TEMPLATES
from tools.email_tool import get_daily_email_summary, get_email_details
from agents.email_agent import EmailAgent, MailAnalysisAgent
from agents.agent_protocol import AgentMessage, MessageType
from ui_components.prompt_ui import render_prompt_automation_ui, render_prompt_history
# 데이터 분석 도구 import
try:
    from tools.data_analysis import DataAnalysisTool, ChartGenerator, InsightExtractor
    DATA_ANALYSIS_AVAILABLE = True
except ImportError as e:
    print(f"데이터 분석 도구 import 실패: {e}")
    DATA_ANALYSIS_AVAILABLE = False
import uuid
from tools.notion_utils import upload_to_notion

# --- Streamlit 페이지 설정 ---
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

# CSS 스타일 적용
apply_custom_css()

# --- 사용자 입력 처리 공통 함수 ---
def play_audio_autoplay_hidden(audio_bytes: bytes):
    if not audio_bytes:
        return
    audio_base64 = base64.b64encode(audio_bytes).decode()
    audio_html = f"""
        <audio autoplay style="display:none">
            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mpeg">
        </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)

def process_user_text_input(text_input: str):
    if not text_input.strip():
        st.warning("내용이 없는 메시지는 처리할 수 없습니다.")
        return
        
    # 대화 기록 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # 사용자 메시지 저장 (UI 표시는 채팅 컨테이너에서 처리)
    st.session_state.messages.append({"role": "user", "content": text_input})
    
    # 상태 표시 컨테이너 생성
    status_container = st.empty()
    
    # --- 진행상황 대시보드 연동: LLM 작업 시작 ---
    st.session_state["current_process"] = {"type": "llm", "desc": "LLM 입력 분석 중...", "progress": 0.1}
    with show_spinner_ui("🤔 생각 중..."):
        # 1단계: 입력 분석
        st.session_state["current_process"]["desc"] = "LLM 입력 분석 중..."
        st.session_state["current_process"]["progress"] = 0.1
        # 2단계: 대화 이력 준비
        st.session_state["current_process"]["desc"] = "대화 이력 준비 중..."
        st.session_state["current_process"]["progress"] = 0.3
        conversation_history = []
        for msg in st.session_state.messages:
            if msg["role"] in ["user", "assistant"]:
                if "voice_text" in msg and "detailed_text" in msg:
                    conversation_history.append({"role": msg["role"], "content": msg["detailed_text"]})
                elif "content" in msg:
                    conversation_history.append({"role": msg["role"], "content": msg["content"]})
        # --- 챗봇 파일 업로드 context 전달 ---
        file_context = None
        if "chatbot_uploaded_file" in st.session_state and st.session_state["chatbot_uploaded_file"]:
            file_context = {"uploaded_file": st.session_state["chatbot_uploaded_file"]}
        # 3단계: LLM 응답 대기 (context 전달 예시)
        st.session_state["current_process"]["desc"] = "LLM 응답 대기 중..."
        st.session_state["current_process"]["progress"] = 0.5
        # 예시: plan_and_execute_workflow 등 context 전달
        # response = coordinator_agent.plan_and_execute_workflow(text_input, context=file_context)
        # 실제로는 아래처럼 context를 agent에 넘기는 구조로 확장 필요
        response = assistant_core.process_command_with_llm_and_tools(text_input, conversation_history)
        # 4단계: LLM 응답 처리
        st.session_state["current_process"]["desc"] = "LLM 응답 처리 중..."
        st.session_state["current_process"]["progress"] = 0.8
        
        # 디버깅을 위해 응답 로그 출력
        # 바이너리 데이터 로깅 방지 - 응답 내용을 안전하게 출력
        safe_response = {}
        for key, value in response.items():
            if key == "audio_content" and isinstance(value, bytes):
                safe_response[key] = f"[Binary audio data of length: {len(value)} bytes]"
            else:
                safe_response[key] = value
        print(f"\n[DEBUG] LLM Response: {safe_response}\n")
        
        if response.get("status") == "success":
            # 응답 타입 확인
            if response.get("response_type") == "audio_response":
                # 음성 및 상세 텍스트 처리
                voice_text = response.get("voice_text", "")
                detailed_text = response.get("detailed_text", voice_text)
                audio_content = response.get("audio_content", None)
                
                # 디버깅 정보 출력 - 바이너리 데이터 로깅 방지 개선
                print(f"\n[DEBUG] Voice Text: {voice_text[:50] if voice_text else 'None'}...\n")
                print(f"\n[DEBUG] Detailed Text: {detailed_text[:50] if detailed_text else 'None'}...\n")
                if isinstance(audio_content, bytes):
                    print(f"\n[DEBUG] Audio Content: Binary data of length {len(audio_content)} bytes\n")
                else:
                    print(f"\n[DEBUG] Audio Content Type: {type(audio_content)}\n")
                
                # 대화 기록에 저장 (UI 표시는 채팅 컨테이너에서 처리)
                if voice_text:
                    # 오디오가 있는 경우 먼저 메시지를 추가
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "voice_text": voice_text,
                        "detailed_text": detailed_text
                    })
                    
                    # 오디오 자동 재생 (UI 없음)
                    if audio_content and isinstance(audio_content, bytes):
                        play_audio_autoplay_hidden(audio_content)
                    else:
                        st.warning("💬 텍스트 응답만 가능합니다. (오디오 생성 실패)")
                else:
                    st.error("어시스턴트 응답 생성 오류")
                    print(f"\n[DEBUG] ERROR: Empty voice_text in audio_response\n")
            
            # text_fallback 응답 타입 처리
            elif response.get("response_type") == "text_fallback" and response.get("text_content"):
                text_content = response.get("text_content")
                print(f"\n[DEBUG] Text Fallback Content: {text_content[:50]}...\n")
                
                # 대화 기록에 저장 (UI 표시는 채팅 컨테이너에서 처리)
                st.session_state.messages.append({
                    "role": "assistant",
                    "voice_text": text_content,
                    "detailed_text": text_content
                })
            
            else:
                # 일반 텍스트 응답
                message = response.get("message", "") or response.get("response", "") or response.get("text_content", "응답이 없습니다.")
                print(f"\n[DEBUG] Text Response Message: {message}\n")
                
                # 대화 기록에 저장 (UI 표시는 채팅 컨테이너에서 처리)
                st.session_state.messages.append({"role": "assistant", "content": message})
        else:
            # 오류 응답 처리
            error_msg = response.get("message", "") or response.get("response", "처리 중 알 수 없는 오류가 발생했습니다.")
            st.error(f"오류: {error_msg}")
            print(f"\n[DEBUG] ERROR Response: {error_msg}\n")
    # --- 진행상황 대시보드 연동: LLM 작업 종료 ---
    st.session_state["current_process"] = None

    # 페이지 리로드하여 새 메시지가 표시되도록 함
    # st.rerun() 호출하지 않음

def save_uploaded_file(uploaded_file):
    """
    업로드된 파일을 files/날짜/파일명 경로에 저장하고, 저장 경로를 반환
    """
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    base_dir = os.path.join("files", today)
    os.makedirs(base_dir, exist_ok=True)
    filename = uploaded_file.name
    save_path = os.path.join(base_dir, filename)
    # Streamlit UploadedFile 객체는 getbuffer()로 바이너리 추출 가능
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return save_path

# CSS 스타일 수정 - Gemini 스타일의 UI로 변경
st.markdown("""
<style>
    /* 전체 페이지 레이아웃 */
    .block-container {
        max-width: 900px !important;
        padding-top: 1rem !important;
        padding-bottom: 0 !important;
    }
    
    /* 헤더 영역 스타일 */
    .main-header {
        text-align: center;
        padding: 5px 0;
        margin-bottom: 10px;
        border-bottom: 1px solid #eee;
    }
    
    /* 채팅 컨테이너 - 투명 배경, 높이 확장 */
    .chat-container {
        max-width: 900px;
        margin: 0 auto;
        height: auto !important; /* 자동 높이 설정 */
        padding: 10px;
        margin-bottom: 10px;
        background-color: transparent;
    }
    
    /* 입력 컨테이너 - 투명 배경 */
    .input-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 5px 0;
        background-color: transparent;
    }
    
    /* 메시지 스타일링 */
    .user-message, .assistant-message {
        margin-bottom: 15px;
        padding: 12px 18px;
        border-radius: 18px;
        max-width: 80%;
        line-height: 1.5;
    }
    
    .user-message {
        background-color: #e1f5fe;
        margin-left: auto;
        margin-right: 0;
        color: #0277bd;
    }
    
    .assistant-message {
        background-color: #f1f1f1;
        margin-left: 0;
        margin-right: auto;
        color: #424242;
    }
    
    /* 메시지 입력 영역 스타일 */
    .stTextArea textarea {
        resize: none;
        padding: 12px;
        font-size: 16px;
        border-radius: 24px;
        border: 1px solid #ddd;
        height: 70px !important;
        box-shadow: none;
    }
    
    /* Streamlit 기본 요소 조정 */
    .stApp header {
        display: none;
    }
    
    .stApp footer {
        display: none;
    }
    
    /* 스크롤바 제거 - 전역적으로 적용 */
    ::-webkit-scrollbar {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
    }
    
    body, .main, .stApp, section[data-testid="stSidebar"] {
        scrollbar-width: none !important;
        -ms-overflow-style: none !important;
    }
    
    /* 추가 Gemini 스타일 요소 */
    .chat-wrapper {
        display: flex;
        flex-direction: column;
        height: 100%;
    }
    
    /* 사이드바 조정 - 원래 상태로 롤백 */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-right: 1px solid #eee;
    }
    
    /* 불필요한 여백 제거 */
    div.stButton > button {
        margin-top: 0;
    }
    
    /* 모든 컨테이너 투명화 */
    div.css-1kyxreq.e115fcil2, div.css-1y4p8pa.e1g8pov61, 
    div.block-container > div, div[data-testid="stVerticalBlock"] > div,
    div.stTextArea, div.stTextInput {
        border: none !important;
        box-shadow: none !important;
        background-color: transparent !important;
    }
    
    /* 컨테이너 내부 패딩 조정 */
    div.block-container {
        padding: 0 !important;
    }
    
    /* 전체 컨텐츠 영역 마진 축소 */
    div[data-testid="stAppViewContainer"] > div {
        margin: 0 !important;
    }
    
    /* 기타 Streamlit 요소 투명화 */
    .css-ffhzg2, .css-10trblm, .css-zt5igj, .css-16idsys, 
    .css-90vs21, .css-1p8k8ky {
        background-color: transparent !important;
    }
    
    /* 모든 카드형 UI 요소 투명화 */
    div[data-testid="stDecoration"], div[data-testid="stToolbar"],
    div[data-testid="stCaptionContainer"], div.stMarkdown,
    div.stForm {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    /* 버튼 스타일 개선 */
    button[kind="primaryFormSubmit"] {
        border-radius: 20px !important;
    }
    
    /* 텍스트 영역 마진 제거 */
    div.stMarkdown {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* 입력 버튼 위치 조정 */
    button[data-testid="baseButton-secondary"] {
        margin-top: 8px !important;
    }
    
    /* 음성 상태 표시 영역 */
    .voice-status-area {
        padding: 5px 10px;
        margin-bottom: 10px;
        border-radius: 8px;
        background-color: rgba(240, 242, 246, 0.4);
    }
    
    /* 오디오 플레이어 스타일 */
    audio {
        display: block !important;
        width: 100% !important;
        margin: 10px 0 !important;
    }
    
    /* 스트림릿 오디오 플레이어 컨테이너 스타일 수정 */
    div[data-testid="stAudio"] {
        margin: 10px 0 !important;
        background-color: transparent !important;
    }
    
    /* 스트림릿 오디오 요소의 부모 컨테이너 스타일 수정 */
    div.element-container div {
        background-color: transparent !important;
    }
    
    /* 마진 제거 및 최소 여백 적용 */
    .element-container, .stAudio, .stAlert {
        margin: 0 !important;
        padding: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 사이드바 UI 구성 ---
with st.sidebar:
    st.markdown('<div class="sidebar-header"><h4>💼 AI 기능</h4></div>', unsafe_allow_html=True)
    # 음성 인식 토글 제거 (챗봇으로 이동)
    st.divider()
    st.markdown("""
    <style>
    .feature-button {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        cursor: pointer;
        transition: all 0.2s;
    }
    .feature-button.active {
        background-color: #e1f5fe !important;
        border: 2px solid #2196f3 !important;
        color: #1976d2 !important;
        font-weight: bold;
    }
    .feature-button:hover {
        background-color: #e9ecef;
        transform: translateY(-2px);
    }
    .feature-icon {
        font-size: 1.2rem;
        margin-right: 8px;
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("<h5>주요 기능</h5>", unsafe_allow_html=True)
    feature_col1, feature_col2 = st.columns(2)
    # 버튼 토글 로직
    def toggle_feature(tab_name):
        st.session_state["current_process"] = None  # 탭 전환 시 대시보드 초기화
        if st.session_state.get("active_feature") == tab_name:
            st.session_state.active_feature = None
        else:
            st.session_state.active_feature = tab_name
            if tab_name == "document":
                st.session_state.active_document_task = None
    with feature_col1:
        if st.button("💬 챗봇", key="btn_chatbot", use_container_width=True):
            toggle_feature("chatbot")
        if st.button("📝 프롬프트", key="btn_prompt", use_container_width=True):
            toggle_feature("prompt")
        if st.button("📄 문서", key="btn_document", use_container_width=True):
            toggle_feature("document")
    with feature_col2:
        if st.button("📧 이메일", key="btn_email", use_container_width=True):
            toggle_feature("email")
        if st.button("📊 분석", key="btn_analysis", use_container_width=True):
            toggle_feature("analysis")
        st.button("🔍 검색", key="btn_search", use_container_width=True, disabled=True)
    st.divider()
    st.markdown("#### ⚡ 프로세스 대시보드")
    proc = st.session_state.get("current_process")
    if proc:
        progress = proc.get("progress", 0.0)
        # 진행률 값 검증 (0~1 사이가 아니면 0.0)
        if not isinstance(progress, (int, float)) or not (0.0 <= progress <= 1.0):
            progress = 0.0
        st.info(proc.get("desc", "진행 중 작업"))
        st.progress(progress)
    else:
        st.caption("진행 중인 작업 없음")
    st.divider()
    st.markdown("<div style='position: fixed; bottom: 20px; font-size: 0.8rem;'>© 2025 My AI Agent</div>", unsafe_allow_html=True)
    # 버튼 강조 스타일 적용
    st.markdown(f"""
    <style>
    button#btn_document.feature-button{{background-color: #e1f5fe; border: 2px solid #2196f3; color: #1976d2; font-weight: bold;}}
    button#btn_chatbot.feature-button{{background-color: #e1f5fe; border: 2px solid #2196f3; color: #1976d2; font-weight: bold;}}
    </style>
    """, unsafe_allow_html=True)

# --- 문서 상세 업무 선택 창 (채팅창 위에 표시) ---
document_tasks = [
    {"name": "문서 신규 작성 자동화", "key": "new_document"},
    {"name": "다중 페르소나 협업 자동화", "key": "persona_collab"},
    {"name": "문서 확장 자동화", "key": "doc_expand"},
    # 추후 업문 추가 가능
]

if st.session_state.get("active_feature") == "document":
    tab_labels = [task["name"] for task in document_tasks]
    tabs = st.tabs(tab_labels)
    for idx, tab in enumerate(tabs):
        with tab:
            if document_tasks[idx]["key"] == "new_document":
                st.markdown("#### 신규 문서 작성")
                # 1. 입력 폼
                with st.form("new_doc_form"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        작성자 = st.selectbox("작성자", list(personas.keys()), key="작성자")
                    with col2:
                        피드백담당자 = st.selectbox("피드백 담당자", list(personas.keys()), key="피드백담당자")
                    with col3:
                        템플릿 = st.selectbox("문서 템플릿", list(DOCUMENT_TEMPLATES.keys()), key="문서템플릿")
                    요구사항 = st.text_area("요구사항 입력", placeholder="예시: 신규 유저 유입 이벤트 기획서 작성", key="요구사항")
                    submitted = st.form_submit_button("문서 생성")
                if submitted:
                    with st.spinner("문서 생성 중..."):
                        if not isinstance(st.session_state.get("current_process"), dict):
                            st.session_state["current_process"] = {"type": "doc", "desc": "문서 초안 생성 중...", "progress": 0.1}
                        st.session_state["current_process"]["desc"] = "문서 초안 생성 중..."
                        st.session_state["current_process"]["progress"] = 0.2
                        result = execute_create_new_planning_document(
                            user_input=요구사항,
                            writer_persona_name=작성자,
                            reviewer_persona_name=피드백담당자,
                            template_name=템플릿
                        )
                        if not isinstance(st.session_state.get("current_process"), dict):
                            st.session_state["current_process"] = {"type": "doc", "desc": "피드백 반영 중...", "progress": 0.5}
                        st.session_state["current_process"]["desc"] = "피드백 반영 중..."
                        st.session_state["current_process"]["progress"] = 0.5
                        st.session_state['draft'] = result.get('draft')
                        st.session_state['feedback'] = result.get('feedback')
                        st.session_state['final_doc'] = result.get('final_doc')
                        st.session_state['notion_url'] = result.get('notion_url')
                        st.session_state['message'] = result.get('message')
                        st.session_state['doc_step'] = 'feedback'  # 1차 생성 완료, 피드백 단계로
                # 2. 결과 및 추가 요구사항 입력
                if st.session_state.get('doc_step') == 'feedback' and st.session_state.get('draft'):
                    st.markdown("#### 초안")
                    st.write(st.session_state['draft'])
                    st.markdown("#### 피드백")
                    st.write(st.session_state['feedback'])
                    추가요구 = st.text_area("추가 요구사항 입력", key="추가요구")
                    if st.button("최종 문서 생성"):
                        # 추가 요구사항을 기존 요구와 합쳐서 최종 생성
                        최종요구 = st.session_state['요구사항'] + "\n" + 추가요구 if 추가요구 else st.session_state['요구사항']
                        with st.spinner("최종 문서 생성 중..."):
                            if not isinstance(st.session_state.get("current_process"), dict):
                                st.session_state["current_process"] = {"type": "doc", "desc": "최종 문서 생성 중...", "progress": 0.1}
                            st.session_state["current_process"]["desc"] = "최종 문서 생성 중..."
                            st.session_state["current_process"]["progress"] = 0.2
                            result = execute_create_new_planning_document(
                                user_input=최종요구,
                                writer_persona_name=st.session_state['작성자'],
                                reviewer_persona_name=st.session_state['피드백담당자'],
                                template_name=st.session_state['문서템플릿']
                            )
                            if not isinstance(st.session_state.get("current_process"), dict):
                                st.session_state["current_process"] = {"type": "doc", "desc": "최종 문서 피드백 반영 중...", "progress": 0.5}
                            st.session_state["current_process"]["desc"] = "최종 문서 피드백 반영 중..."
                            st.session_state["current_process"]["progress"] = 0.5
                            st.session_state['final_doc'] = result.get('final_doc')
                            st.session_state['notion_url'] = result.get('notion_url')
                            st.session_state['message'] = result.get('message')
                            st.session_state['doc_step'] = 'final'  # 최종 생성 단계
                if st.session_state.get('doc_step') == 'final' and st.session_state.get('final_doc'):
                    st.success("최종 문서가 생성되었습니다!")
                    st.markdown("#### 최종 문서")
                    st.write(st.session_state['final_doc'])
                    if st.session_state.get('notion_url'):
                        st.markdown(f"[Notion에서 문서 확인하기]({st.session_state['notion_url']})")
                    st.info(st.session_state.get('message', ''))
            elif document_tasks[idx]["key"] == "persona_collab":
                st.markdown("#### 다중 페르소나 협업 자동화")
                with st.form("collab_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        프로젝트제목 = st.text_input("프로젝트 제목", key="collab_프로젝트제목")
                        초안작성자 = st.selectbox("초안 작성자", list(personas.keys()), key="collab_초안작성자")
                        검토자 = st.selectbox("검토자", list(personas.keys()), key="collab_검토자")
                    with col2:
                        템플릿 = st.selectbox("문서 템플릿", list(DOCUMENT_TEMPLATES.keys()), key="collab_문서템플릿")
                        업무분배 = st.multiselect("업무 분배 페르소나(2명 이상)", list(personas.keys()), key="collab_업무분배")
                    요구사항 = st.text_area("요구사항 입력", placeholder="예시: 신규 프로젝트 협업 계획 작성", key="collab_요구사항")
                    submitted = st.form_submit_button("협업 계획 생성")
                if submitted:
                    if len(업무분배) < 2:
                        st.warning("업무 분배 페르소나는 2명 이상 선택해야 합니다.")
                    else:
                        if not isinstance(st.session_state.get("current_process"), dict):
                            st.session_state["current_process"] = {"type": "doc", "desc": "협업 계획 초안 생성 중...", "progress": 0.1}
                        with st.spinner("협업 계획 생성 중..."):
                            st.session_state["current_process"]["desc"] = "협업 계획 초안 생성 중..."
                            st.session_state["current_process"]["progress"] = 0.2
                            result = execute_collaboration_planning(
                                project_title=프로젝트제목,
                                base_document_type=템플릿,
                                user_requirements=요구사항,
                                writer_persona_name=초안작성자,
                                allocate_to_persona_names=업무분배,
                                review_by_persona_name=검토자
                            )
                            if not isinstance(st.session_state.get("current_process"), dict):
                                st.session_state["current_process"] = {"type": "doc", "desc": "협업 계획 피드백/통합 중...", "progress": 0.7}
                            st.session_state["current_process"]["desc"] = "협업 계획 피드백/통합 중..."
                            st.session_state["current_process"]["progress"] = 0.7
                            st.session_state['collab_result'] = result
                        st.session_state["current_process"] = None
            elif document_tasks[idx]["key"] == "doc_expand":
                st.markdown("#### 문서 확장 자동화")
                with st.form("expand_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        참조키워드 = st.text_input("참조 문서 키워드", key="expand_참조키워드")
                        작성자 = st.selectbox("작성자", list(personas.keys()), key="expand_작성자")
                    with col2:
                        신규템플릿 = st.selectbox("신규 문서 템플릿", list(DOCUMENT_TEMPLATES.keys()), key="expand_신규템플릿")
                        추가요구 = st.text_area("추가 요구사항 입력", key="expand_추가요구")
                    submitted = st.form_submit_button("문서 확장 생성")
                if submitted:
                    if not isinstance(st.session_state.get("current_process"), dict):
                        st.session_state["current_process"] = {"type": "doc", "desc": "문서 확장 초안 생성 중...", "progress": 0.1}
                    with st.spinner("문서 확장 생성 중..."):
                        st.session_state["current_process"]["desc"] = "문서 확장 초안 생성 중..."
                        st.session_state["current_process"]["progress"] = 0.2
                        result = execute_expand_notion_document(
                            keyword=참조키워드,
                            new_doc_type=신규템플릿,
                            extra_requirements=추가요구,
                            writer_persona_name=작성자
                        )
                        if not isinstance(st.session_state.get("current_process"), dict):
                            st.session_state["current_process"] = {"type": "doc", "desc": "문서 확장 피드백/통합 중...", "progress": 0.7}
                        st.session_state["current_process"]["desc"] = "문서 확장 피드백/통합 중..."
                        st.session_state["current_process"]["progress"] = 0.7
                        st.session_state['expand_result'] = result
                    st.session_state["current_process"] = None
            else:
                st.markdown(f"### {document_tasks[idx]['name']}")
                st.markdown(f"<div style='margin-top:32px;'><b>{document_tasks[idx]['name']}</b> 업문 영역 (추후 구현)</div>", unsafe_allow_html=True)

# --- 데이터 분석 탭 구현 ---
if st.session_state.get("active_feature") == "analysis":
    st.markdown("#### 📊 데이터 분석")
    
    if not DATA_ANALYSIS_AVAILABLE:
        st.error("데이터 분석 도구를 불러올 수 없습니다. 필요한 의존성이 설치되어 있는지 확인해주세요.")
        st.session_state["current_process"] = None  # 에러 시 대시보드 초기화
        st.stop()
    
    # 파일 업로드 (최상단)
    uploaded_file = st.file_uploader(
        "분석할 파일을 업로드하세요",
        type=['csv', 'xlsx', 'xls', 'pdf'],
        help="CSV, Excel, PDF 파일을 지원합니다."
    )
    
    if uploaded_file:
        # 파일 저장 및 경로 전달
        save_path = save_uploaded_file(uploaded_file)
        st.session_state['uploaded_file_path'] = save_path
        st.info(f"업로드 파일이 저장되었습니다: {save_path}")
        # 데이터 분석 도구 초기화
        analysis_tool = DataAnalysisTool()
        insight_extractor = InsightExtractor()
        
        # 파일 처리
        if not isinstance(st.session_state.get("current_process"), dict):
            st.session_state["current_process"] = {"type": "analysis", "desc": "파일 분석 중...", "progress": 0.1}
        else:
            st.session_state["current_process"] = {"type": "analysis", "desc": "파일 분석 중...", "progress": 0.1}
        error_occurred = False
        try:
            # 저장된 경로를 분석 도구에 전달
            result = analysis_tool.process_uploaded_file(save_path)
            if not isinstance(st.session_state.get("current_process"), dict):
                st.session_state["current_process"] = {"type": "analysis", "desc": "데이터 처리 완료", "progress": 0.3}
            st.session_state["current_process"]["desc"] = "데이터 처리 완료"
            st.session_state["current_process"]["progress"] = 0.3
        except Exception as e:
            st.session_state["current_process"] = None
            st.error(f"파일 처리 중 오류: {str(e)}")
            error_occurred = True
        
        if not error_occurred:
            if result.get("success"):
                # 여러 표가 있는 경우 표 선택
                tables = result.get("tables", [])
                
                if len(tables) > 1:
                    st.subheader("📋 발견된 표 목록")
                    table_names = [table["name"] for table in tables]
                    selected_table_idx = st.selectbox(
                        "분석할 표를 선택하세요:",
                        range(len(tables)),
                        format_func=lambda x: table_names[x]
                    )
                    selected_table = tables[selected_table_idx]
                    df = selected_table["data"]
                    
                    # 다른 표들도 미리보기로 표시
                    with st.expander(f"더 보기 ({len(tables)-1}개)"):
                        for i, table in enumerate(tables):
                            if i != selected_table_idx:
                                st.write(f"**{table['name']}** ({table['data'].shape[0]}행 x {table['data'].shape[1]}열)")
                                st.dataframe(table['data'].head(5), use_container_width=True)
                                st.divider()
                elif len(tables) == 1:
                    df = result["data"]
                else:
                    df = None
                
                # 원본 데이터 미리보기
                st.subheader("📋 원본 데이터 미리보기")
                if df is not None:
                    st.dataframe(df.head(10), use_container_width=True)
                elif result.get("text"):
                    st.info("PDF에서 표를 찾지 못했습니다. 전체 텍스트 요약을 표시합니다.")
                    st.text_area("PDF 텍스트 요약", value=result["text"][:2000], height=300)
                else:
                    st.warning("표 또는 텍스트 데이터가 없습니다.")
                
                # 탭 생성
                tab1, tab2 = st.tabs(["📊 데이터 분석", "📈 시각화 분석"])
                
                with tab1:
                    # LLM 기반 데이터 내용 분석
                    st.session_state["current_process"]["desc"] = "데이터 내용 분석 중..."
                    st.session_state["current_process"]["progress"] = 0.5
                    analysis_result = insight_extractor.analyze_data_content(df, uploaded_file.name)
                    st.session_state["current_process"]["desc"] = "분석 완료"
                    # 분석 결과 Notion 업로드 버튼 추가
                    if analysis_result and analysis_result.get("analysis"):
                        if st.button("분석 결과 Notion에 업로드", type="primary"):
                            notion_title = f"{uploaded_file.name} 분석 결과"
                            notion_content = analysis_result["analysis"]
                            success, url_or_msg = upload_to_notion(notion_title, notion_content)
                            if success:
                                st.success(f"분석 결과가 Notion에 업로드되었습니다! [바로가기]({url_or_msg})")
                            else:
                                st.error(f"Notion 업로드 실패: {url_or_msg}")
                    st.session_state["current_process"]["progress"] = 1.0
                    
                    if analysis_result.get("success"):
                        # 분석 결과 표시
                        st.subheader("🔍 데이터 분석 결과")
                        st.markdown(analysis_result["analysis"])
                    else:
                        st.error(f"분석 실패: {analysis_result.get('error')}")
                        st.session_state["current_process"] = None
                
                with tab2:
                    # 시각화 분석 탭
                    st.subheader("📈 시각화 분석")
                    
                    # 사용 가능한 시각화 옵션 가져오기
                    available_viz = insight_extractor.get_available_visualizations(df)
                    
                    # 시각화 옵션 선택
                    st.write("원하는 시각화 자료를 선택하세요 (중복 선택 가능):")
                    
                    selected_viz = []
                    for category, viz_options in available_viz.items():
                        if viz_options:  # 옵션이 있는 카테고리만 표시
                            st.write(f"**{category}:**")
                            for option in viz_options:
                                if st.checkbox(option, key=f"viz_{option}"):
                                    selected_viz.append(option)
                            st.write("")  # 빈 줄 추가
                    
                    # 시각화 생성 버튼
                    if st.button("시각화 자료 생성", type="primary"):
                        if selected_viz:
                            if not isinstance(st.session_state.get("current_process"), dict):
                                st.session_state["current_process"] = {"type": "visualization", "desc": "시각화 생성 중...", "progress": 0.1}
                            st.session_state["current_process"]["desc"] = "시각화 생성 중..."
                            st.session_state["current_process"]["progress"] = 0.2
                            
                            # 선택된 시각화 생성
                            visualizations = insight_extractor.generate_selected_visualizations(df, selected_viz)
                            st.session_state["current_process"]["desc"] = "시각화 완료"
                            st.session_state["current_process"]["progress"] = 1.0
                            
                            if visualizations:
                                st.success(f"선택하신 {len(visualizations)}개의 시각화 자료가 생성되었습니다.")
                                
                                # 시각화를 2개씩 나누어 표시
                                for i in range(0, len(visualizations), 2):
                                    cols = st.columns(2)
                                    for j in range(2):
                                        if i + j < len(visualizations):
                                            with cols[j]:
                                                viz = visualizations[i + j]
                                                st.plotly_chart(viz["figure"], use_container_width=True)
                            else:
                                st.warning("선택하신 시각화 자료를 생성할 수 없습니다.")
                            st.session_state["current_process"] = None
                        else:
                            st.warning("시각화 자료를 선택해주세요.")
                
            else:
                st.error(result.get("error", "파일 처리 중 오류가 발생했습니다."))
                st.session_state["current_process"] = None

# --- 이메일 탭 개선: 메일함 연동 및 메일 선택 UI 추가 (mock 데이터 기반 예시) ---
if st.session_state.get("active_feature") == "email":
    import datetime
    st.markdown("#### 메일 조회")
    if "selected_email_date" not in st.session_state:
        st.session_state.selected_email_date = datetime.date.today()
    selected_date = st.date_input("날짜 선택", value=st.session_state.selected_email_date, key="email_date_input")
    st.session_state.selected_email_date = selected_date
    # days_ago 계산 (오늘=0, 어제=1 ...)
    # --- 대시보드 연동: 메일 목록 조회 시작 ---
    st.session_state["current_process"] = {"type": "email", "desc": "메일 목록 조회 중...", "progress": 0.1}
    days_ago = (datetime.date.today() - selected_date).days
    result = get_daily_email_summary(days_ago=days_ago, max_results=10)
    st.session_state["current_process"]["desc"] = "메일 목록 분석 중..."
    st.session_state["current_process"]["progress"] = 0.3
    if result["status"] == "success":
        real_emails = result["emails"]
    else:
        st.error(result.get("error", "메일 조회 실패"))
        real_emails = []
    st.session_state["current_process"] = None
    # 실제 메일 분석 에이전트 사용
    mail_analysis_agent = MailAnalysisAgent()
    
    def analyze_mail_with_agent(mail):
        try:
            st.session_state["current_process"] = {"type": "email", "desc": "이메일 본문 분석 중...", "progress": 0.1}
            st.session_state["current_process"]["desc"] = "이메일 본문 분석 중..."
            st.session_state["current_process"]["progress"] = 0.2
            # 메일 분석을 위한 데이터 준비
            analysis_data = {
                "email_body": mail.get('body', ''),
                "email_subject": mail.get('subject', ''),
                "email_from": mail.get('from', ''),
                "email_date": mail.get('date', '')
            }
            
            # MailAnalysisAgent로 분석 요청
            analysis_result = mail_analysis_agent.process_task(analysis_data)
            st.session_state["current_process"]["desc"] = "자동 답장 생성 중..."
            st.session_state["current_process"]["progress"] = 0.5
            
            if analysis_result.get('status') == 'success':
                return {
                    'summary': analysis_result.get('analysis', '분석 완료'),
                    'importance': analysis_result.get('importance', '일반'),
                    'action': analysis_result.get('action', '참조만 해도 됨'),
                    'reason': analysis_result.get('reason', '분석 완료')
                }
            else:
                # 분석 실패 시 fallback
                return {
                    'summary': f"{mail.get('body', mail.get('subject', ''))[:20]}...",
                    'importance': '일반',
                    'action': '참조만 해도 됨',
                    'reason': '분석 실패'
                }
        except Exception as e:
            st.session_state["current_process"] = None
            # 예외 발생 시 fallback
            return {
                'summary': f"{mail.get('body', mail.get('subject', ''))[:20]}...",
                'importance': '일반',
                'action': '참조만 해도 됨',
                'reason': f'오류: {str(e)}'
            }
    
    mail_rows = []
    for m in real_emails:
        analysis = analyze_mail_with_agent(m)
        mail_rows.append({
            'id': m.get('message_id', m.get('id', '')),
            '제목': m.get('subject', ''),
            '핵심 내용': analysis['summary'],
            '중요도': analysis['importance'],
            '의사결정': analysis['action'],
            '분석 근거': analysis['reason'],
            '첨부파일': '없음'  # 첨부파일 연동은 추후 구현
        })
    if not mail_rows:
        st.info("해당 날짜에 받은 메일이 없습니다.")
    else:
        import pandas as pd
        df = pd.DataFrame(mail_rows)
        
        # 표에서 메일 선택 기능 구현
        st.markdown("### 📧 메일 목록")
        
        # streamlit-aggrid 임포트
        from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
        
        # 표용 데이터 준비 (제목, 중요도, 의사결정만)
        table_data = df[['제목', '중요도', '의사결정']].copy()
        
        # 중요도 등급 매핑 (커스텀 정렬용)
        importance_order = {'매우 중요': 1, '중요': 2, '일반': 3, '낮음': 4}
        table_data['중요도_정렬'] = table_data['중요도'].map(importance_order).fillna(99).astype(int)
        
        # AgGrid 옵션 빌더
        gb = GridOptionsBuilder.from_dataframe(table_data)
        gb.configure_selection('single', use_checkbox=False)
        gb.configure_column('제목', header_name='메일 제목', width=400)
        gb.configure_column('중요도', header_name='중요도', width=100, sortable=True)
        gb.configure_column('의사결정', header_name='의사결정', width=120)
        gb.configure_column('중요도_정렬', hide=True, sort='asc')  # 숨김 + 기본 정렬
        grid_options = gb.build()
        
        # AgGrid 표 표시 및 선택
        grid_response = AgGrid(
            table_data,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            fit_columns_on_grid_load=True,
            allow_unsafe_jscode=True,
            height=350,
            theme='streamlit',
            reload_data=True
        )
        
        # 선택된 행 인덱스 추출
        selected_idx = 0
        selected_rows = grid_response.get('selected_rows', [])
        if isinstance(selected_rows, list) and len(selected_rows) > 0 and isinstance(selected_rows[0], dict):
            selected_row = selected_rows[0]
            match = df[df['제목'] == selected_row['제목']]
            if not match.empty:
                selected_idx = match.index[0]
        st.session_state.selected_mail_index = selected_idx
        selected_mail = real_emails[selected_idx]
        
        st.markdown("---")
        st.markdown("### 📋 선택된 메일 상세")
        st.markdown(f"**제목:** {selected_mail.get('subject','')}  ")
        st.markdown(f"**발신자:** {selected_mail.get('from','')}  ")
        st.markdown(f"**날짜:** {selected_mail.get('date','')}  ")
        st.markdown(f"**첨부파일:** 없음  ")
        
        # 본문 상세 조회 (message_id로 get_email_details 호출)
        detail = get_email_details(selected_mail.get('message_id', ''))
        body = detail.get('body', '(본문 없음)')
        st.markdown(f"**본문:**\n{body}")
        # 하단 상세 업문: 자동 답장, 첨부파일 추출 UI (기존 코드 유지)
        email_tasks = [
            {"name": "자동 답장", "key": "auto_reply"},
            {"name": "첨부파일 추출", "key": "attachment_extract"},
        ]
        tab_labels = [task["name"] for task in email_tasks]
        tabs = st.tabs(tab_labels)
        email_agent = EmailAgent()
        for idx, tab in enumerate(tabs):
            with tab:
                if email_tasks[idx]["key"] == "auto_reply":
                    st.markdown("#### 자동 답장")
                    with st.form("email_reply_form"):
                        추가지시 = st.text_area("추가 지시사항 (선택)", placeholder="답장에 반영할 추가 요청사항", key="reply_extra")
                        submitted = st.form_submit_button("자동 답장 생성")
                    if submitted:
                        subject = selected_mail.get('subject', '')
                        body = selected_mail.get('body', '')
                        sender = selected_mail.get('from', '')
                        history = '\n'.join(selected_mail.get('history', []))
                        tone = "정중하고 간결한 비즈니스 톤"
                        task_id = f"email_{uuid.uuid4().hex}"
                        agent_message = AgentMessage(
                            sender_id="ui",
                            receiver_id="email_agent",
                            message_type=MessageType.TASK_REQUEST.value,
                            content={
                                "task_id": task_id,
                                "task_data": {
                                    "type": "generate_reply",
                                    "email_id": selected_mail.get('message_id', ''),
                                    "subject": subject,
                                    "body": body,
                                    "from": sender,
                                    "history": history,
                                    "tone": tone,
                                    "extra_instruction": 추가지시
                                }
                            },
                            id=f"msg_{uuid.uuid4().hex}"
                        )
                        reply_result = email_agent._handle_task_request(agent_message)
                        reply_draft = reply_result.get('result', {}).get('reply', '[답장 생성 실패]')
                        st.session_state['email_reply_draft'] = reply_draft
                    reply_draft = st.session_state.get('email_reply_draft', '')
                    reply_text = st.text_area("답장 초안 (수정 가능)", value=reply_draft, key="reply_draft_edit")
                    send_clicked = st.button("답장 발송")
                    if send_clicked and reply_text.strip():
                        send_task_id = f"email_{uuid.uuid4().hex}"
                        send_message = AgentMessage(
                            sender_id="ui",
                            receiver_id="email_agent",
                            message_type=MessageType.TASK_REQUEST.value,
                            content={
                                "task_id": send_task_id,
                                "task_data": {
                                    "type": "send_reply",
                                    "email_id": selected_mail.get('message_id', ''),
                                    "reply_body": reply_text
                                }
                            },
                            id=f"msg_{uuid.uuid4().hex}"
                        )
                        send_result = email_agent._handle_task_request(send_message)
                        if send_result.get('result', {}).get('status') == 'success':
                            st.success("답장이 성공적으로 발송되었습니다.")
                        else:
                            st.error(f"답장 발송 실패: {send_result.get('result', {}).get('error', '알 수 없는 오류')}")
                elif email_tasks[idx]["key"] == "attachment_extract":
                    st.markdown("#### 첨부파일 추출")
                    with st.form("email_attachment_form"):
                        첨부파일 = st.multiselect("첨부파일", [a['filename'] for a in selected_mail.get('attachments', [])], default=[a['filename'] for a in selected_mail.get('attachments', [])], key="extract_attachments")
                        submitted = st.form_submit_button("첨부파일 저장")
                    if submitted:
                        # TODO: 첨부파일 저장 로직 연동
                        st.session_state['email_attachment_result'] = {
                            'saved_files': [f"/local/path/{f}" for f in 첨부파일] if 첨부파일 else []
                        }
                    if st.session_state.get('email_attachment_result'):
                        res = st.session_state['email_attachment_result']
                        st.markdown("**저장된 파일 경로**")
                        for path in res['saved_files']:
                            st.write(path)
                else:
                    st.markdown(f"### {email_tasks[idx]['name']}")
                    st.markdown(f"<div style='margin-top:32px;'><b>{email_tasks[idx]['name']}</b> 업문 영역 (추후 구현)</div>", unsafe_allow_html=True)

# --- 프롬프트 자동화 UI ---
if st.session_state.get("active_feature") == "prompt":
    render_prompt_automation_ui()
    render_prompt_history()

# --- 메인 UI 레이아웃 ---
if st.session_state.get("active_feature") in [None, "chatbot"]:
    st.markdown("<div class='chat-wrapper'>", unsafe_allow_html=True)

    # 음성 인식 토글 (챗봇 상단, 헤더 위)
    voice_active = st.toggle(
        "🎤 음성 인식", 
        value=st.session_state.voice_recognition_active,
        help="켜면 음성 명령을 자동으로 감지합니다",
        key="voice_toggle"
    )
    if voice_active != st.session_state.voice_recognition_active:
        st.session_state.voice_recognition_active = voice_active
        st.rerun()
    if st.session_state.voice_recognition_active:
        st.success("🎤 음성 인식이 활성화되었습니다", icon="🎙️")

    # 간소화된 헤더
    st.markdown('<div class="main-header"><h3>AI 기획 비서</h3></div>', unsafe_allow_html=True)

    # 채팅 컨테이너 - 메시지 표시 영역 (높이 확장)
    with st.container():
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        # 이전 대화 기록 표시 - system 메시지는 제외
        for message in st.session_state.messages:
            if message["role"] == "system":
                continue  # 시스템 메시지는 표시하지 않음
            elif message["role"] == "user":
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end;">
                    <div class="user-message">
                        {message["content"]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            elif message["role"] == "assistant":
                if "voice_text" in message and "detailed_text" in message:
                    # 음성 답변과 상세 답변이 있는 경우
                    if message["voice_text"] == message["detailed_text"]:
                        # 음성과 상세 답변이 같은 경우
                        st.markdown(f"""
                        <div style="display: flex; justify-content: flex-start;">
                            <div class="assistant-message">
                                {message["voice_text"]}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # 음성과 상세 답변이 다른 경우
                        st.markdown(f"""
                        <div style="display: flex; justify-content: flex-start;">
                            <div class="assistant-message">
                                <p>{message["voice_text"]}</p>
                                <details>
                                    <summary>상세 정보</summary>
                                    <div style="padding: 10px 0;">
                                        {message["detailed_text"]}
                                    </div>
                                </details>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                elif "content" in message:
                    # 일반 텍스트 답변
                    st.markdown(f"""
                    <div style="display: flex; justify-content: flex-start;">
                        <div class="assistant-message">
                            {message["content"]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 챗봇 입력 영역 위에 파일 업로드 UI 추가
    st.markdown('#### 📎 챗봇 파일 업로드')
    chatbot_uploaded_file = st.file_uploader('챗봇에서 사용할 파일을 업로드하세요', type=['csv', 'xlsx', 'xls', 'pdf'], key='chatbot_file_uploader')
    if chatbot_uploaded_file:
        st.session_state['chatbot_uploaded_file'] = chatbot_uploaded_file

    # 입력 컨테이너 - 텍스트 입력 영역 (항상 하단에 노출, 기존 방식)
    with st.container():
        st.markdown('<div class="input-container">', unsafe_allow_html=True)
        def submit_message():
            if st.session_state.text_input.strip():
                process_user_text_input(st.session_state.text_input)
                st.session_state.text_input = ""
        st.text_input(
            "메시지 입력",
            key="text_input",
            value=st.session_state.text_input,
            placeholder="메시지를 입력하고 Enter를 누르면 전송됩니다...",
            label_visibility="collapsed",
            on_change=submit_message
        )
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# --- 오디오 자동 재생 함수 ---
def play_audio_in_browser(audio_bytes: bytes):
    """
    주어진 오디오 바이트를 브라우저에서 자동 재생합니다.
    """
    if not audio_bytes:
        return
    try:
        # (audio_html 및 st.markdown(audio_html, ...) 코드 완전 삭제)
        pass
    except Exception as e:
        st.error(f"음성 재생 중 오류 발생: {e}")

# --- Voice Recognition Functions ---
def get_voice_input_once():
    """
    단일 음성 입력을 가져옵니다. (버튼 입력용)
    """
    status_placeholder = st.empty()
    r = sr.Recognizer()
    
    with sr.Microphone() as source:
        status_placeholder.info("🎤 마이크 설정 중... (주변 소음 측정)")
        try:
            r.adjust_for_ambient_noise(source, duration=0.5)
            status_placeholder.info("🔊 듯고 있어요... 말씀해주세요.")
            audio = r.listen(source, timeout=7, phrase_time_limit=15)
        except sr.WaitTimeoutError:
            status_placeholder.warning("⏰ 음성 입력 시간이 초과되었습니다.")
            return None
        except Exception as e:
            status_placeholder.error(f"⚠️ 마이크 오류: {e}")
            return None

    status_placeholder.info("🤖 음성 인식 중...")
    try:
        result = speech_to_text_from_mic_data(audio)
        if result and result.get("status") == "success" and result.get("text"):
            text = result.get("text")
            status_placeholder.success(f"✅ 인식됨: {text}")
            return text
        else:
            status_placeholder.error("❓ 음성 인식 실패")
            return None
    except Exception as e:
        status_placeholder.error(f"⚠️ 인식 오류: {e}")
        return None

def start_continuous_voice_recognition():
    """
    음성 인식을 지속적으로 감지하는 스레드를 시작합니다.
    """
    if "voice_thread" not in st.session_state or not st.session_state.voice_thread or not st.session_state.voice_thread.is_alive():
        st.session_state.voice_thread = threading.Thread(target=continuous_voice_listener, daemon=True)
        st.session_state.voice_thread.start()
        return True
    return False

def stop_continuous_voice_recognition():
    """
    음성 인식 스레드를 중지합니다.
    """
    st.session_state.voice_recognition_active = False
    return True

def continuous_voice_listener():
    """
    백그라운드에서 음성을 지속적으로 듯고 처리하는 함수
    """
    # 채팅 컨테이너 내에 음성 상태 표시 영역 생성
    voice_status_container = st.container()
    with voice_status_container:
        voice_status_placeholder = st.empty()
        voice_status_placeholder.markdown('<div class="voice-status-area"></div>', unsafe_allow_html=True)
    
    # 인식기 초기화
    r = sr.Recognizer()
    r.pause_threshold = 1.0  # 음성 인식 문장 사이의 휴지 시간(초)
    r.energy_threshold = 1000  # 마이크 소음 감지 임계값
    
    try:
        with sr.Microphone() as source:
            # 소음 조정
            voice_status_placeholder.markdown('<div class="voice-status-area">' + show_voice_status("processing", "소음 초기화 중") + '</div>', unsafe_allow_html=True)
            r.adjust_for_ambient_noise(source, duration=0.5)
            
            while st.session_state.voice_recognition_active:
                voice_status_placeholder.markdown('<div class="voice-status-area">' + show_voice_status("listening", "음성 감지 중") + '</div>', unsafe_allow_html=True)
                try:
                    # 마이크에서 오디오 감지 (3초 이내 음성 감지 시간제한)
                    audio = r.listen(source, timeout=3, phrase_time_limit=10)
                    
                    # 음성 인식 중
                    voice_status_placeholder.markdown('<div class="voice-status-area">' + show_voice_status("processing", "인식 중") + '</div>', unsafe_allow_html=True)
                    result = speech_to_text_from_mic_data(audio)
                    
                    if result and result.get("status") == "success" and result.get("text"):
                        text = result.get("text")
                        if text and len(text.strip()) > 0:
                            voice_status_placeholder.markdown('<div class="voice-status-area">' + show_voice_status("processing", f"인식됨: {text}") + '</div>', unsafe_allow_html=True)
                            # 음성 명령 처리
                            process_user_text_input(text)
                            time.sleep(1)  # 음성 처리 후 잠시 대기
                    
                except sr.WaitTimeoutError:
                    # 음성이 감지되지 않았음 - 공문 경우
                    pass
                    
                except Exception as e:
                    voice_status_placeholder.markdown('<div class="voice-status-area">' + show_voice_status("error", f"오류: {str(e)[:50]}") + '</div>', unsafe_allow_html=True)
                    time.sleep(3)  # 오류 표시 후 잠시 대기

    except Exception as e:
        voice_status_placeholder.markdown('<div class="voice-status-area">' + show_voice_status("error", f"마이크 오류: {str(e)[:50]}") + '</div>', unsafe_allow_html=True)

# --- 음성 인식 토글 상태 확인 및 처리 ---
if st.session_state.voice_recognition_active:
    # 토글이 켜져 있으면 음성 인식 스레드 시작
    start_continuous_voice_recognition()
else:
    # 토글이 꺼져 있으면 음성 인식 중지 시도
    if "voice_thread" in st.session_state and st.session_state.voice_thread and st.session_state.voice_thread.is_alive():
        stop_continuous_voice_recognition()

def main():
    """
    애플리케이션 메인 함수
    
    이 함수는 앱이 직접 실행될 때 호출됩니다.
    Streamlit은 이미 모든 UI 로직을 실행하므로 여기서는 
    추가적인 초기화나 설정 작업을 수행할 수 있습니다.
    """
    logger.info(f"{config.APP_NAME} v{config.APP_VERSION} 시작됨")
    
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
        
        // 24시간마다 캐시 초기화 (86400000 밀리초)
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
    
    # 애플리케이션 시작 시 추가 설정이나 검증 작업을 여기에 추가할 수 있습니다
    if config.is_development():
        logger.debug("개발 모드에서 실행 중")

if __name__ == "__main__":
    main()