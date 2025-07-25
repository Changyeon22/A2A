# ui_components/prompt_ui.py
"""
프롬프트 자동화 UI 컴포넌트
- 기본/심화 모드 탭
- 실시간 미리보기
- 결과물 관리 (피드백, 수정, 저장, 복사)
"""
import streamlit as st
import json
import pyperclip
from typing import Dict, Any, Optional
from agents.coordinator_agent import CoordinatorAgent

def render_prompt_automation_ui():
    """프롬프트 자동화 메인 UI"""
    
    st.header("프롬프트 자동화")
    st.markdown("AI가 고퀄리티 프롬프트를 자동으로 설계하고 개선해드립니다.")
    
    # 탭 생성
    tab1, tab2 = st.tabs(["기본 모드", "심화 모드"])
    
    with tab1:
        render_basic_prompt_ui()
    
    with tab2:
        render_advanced_prompt_ui()

def render_basic_prompt_ui():
    """기본 프롬프트 모드 UI"""
    
    st.subheader("기본 프롬프트 생성")
    st.markdown("간단한 목적과 요구사항만 입력하면 AI가 프롬프트를 생성합니다.")
    
    # 입력 폼
    with st.form("basic_prompt_form"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            user_input = st.text_area(
                "프롬프트 목적",
                placeholder="예: 마케팅 이메일 작성, 코드 리뷰, 콘텐츠 요약 등",
                height=100
            )
            
            # 기본 옵션 추가
            output_format = st.selectbox(
                "출력 형식",
                ["일반 텍스트", "목록", "표", "에세이", "코드"],
                help="원하는 출력 형식을 선택하세요"
            )
        
        with col2:
            domain = st.selectbox(
                "도메인",
                ["일반", "마케팅", "개발", "디자인", "교육", "비즈니스"],
                help="도메인 전문가의 피드백을 받을 분야를 선택하세요"
            )
            
            tone = st.selectbox(
                "톤앤매너",
                ["전문적", "친근한", "격식있는", "창의적", "간결한"],
                help="원하는 톤앤매너를 선택하세요"
            )
            
            examples_needed = st.checkbox(
                "예시 포함",
                value=True,
                help="프롬프트에 구체적인 예시 포함"
            )
        
        submitted = st.form_submit_button("프롬프트 생성", type="primary")
    
    if submitted and user_input.strip():
        # 기본 옵션 구성
        basic_options = {
            "tone": tone,
            "output_format": output_format,
            "examples_needed": examples_needed,
            "complexity": "보통"
        }
        process_basic_prompt(user_input, domain, basic_options)

def render_advanced_prompt_ui():
    """심화 프롬프트 모드 UI"""
    
    st.subheader("심화 프롬프트 생성")
    st.markdown("상세한 옵션과 요구사항을 설정하여 고품질 프롬프트를 생성합니다.")
    
    # 입력 폼
    with st.form("advanced_prompt_form"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            user_input = st.text_area(
                "프롬프트 목적",
                placeholder="구체적인 목적과 요구사항을 상세히 입력하세요",
                height=100
            )
            
            target_audience = st.text_input(
                "대상",
                placeholder="예: 개발자, 마케터, 학생 등",
                help="프롬프트 결과물의 대상 사용자"
            )
            
            output_format = st.text_area(
                "출력 형식",
                placeholder="예: JSON, 마크다운, 표 형태, 단락 등",
                height=80
            )
            
            constraints = st.text_area(
                "제약사항",
                placeholder="예: 500자 이내, 특정 용어 사용 금지 등",
                height=80,
                help="프롬프트에 적용할 제약사항"
            )
        
        with col2:
            domain = st.selectbox(
                "도메인",
                ["일반", "마케팅", "개발", "디자인", "교육", "비즈니스"],
                help="도메인 전문가의 피드백을 받을 분야"
            )
            
            complexity = st.select_slider(
                "복잡도",
                options=["간단", "보통", "복잡", "매우 복잡"],
                value="보통",
                help="프롬프트의 복잡도 수준"
            )
            
            creativity = st.slider(
                "창의성",
                min_value=0,
                max_value=10,
                value=5,
                help="창의적/혁신적 요소의 정도"
            )
            
            examples_needed = st.checkbox(
                "예시 포함",
                value=True,
                help="프롬프트에 구체적인 예시 포함"
            )
            
            include_context = st.checkbox(
                "맥락 정보 포함",
                value=False,
                help="배경 정보나 맥락을 포함"
            )
        
        submitted = st.form_submit_button("고급 프롬프트 생성", type="primary")
    
    if submitted and user_input.strip():
        # 고급 옵션 구성
        advanced_options = {
            "target_audience": target_audience,
            "output_format": output_format,
            "constraints": constraints,
            "complexity": complexity,
            "creativity": creativity,
            "examples_needed": examples_needed,
            "include_context": include_context
        }
        process_advanced_prompt(user_input, domain, advanced_options)

def process_basic_prompt(user_input: str, domain: str, options: Dict[str, Any]):
    """기본 프롬프트 처리"""
    # 대시보드 연동: 프롬프트 생성 시작
    if not isinstance(st.session_state.get("current_process"), dict):
        st.session_state["current_process"] = {}
    st.session_state["current_process"]["desc"] = "기본 프롬프트 생성 중..."
    st.session_state["current_process"]["progress"] = 0.1
    coordinator = CoordinatorAgent()
    if not isinstance(st.session_state.get("current_process"), dict):
        st.session_state["current_process"] = {}
    st.session_state["current_process"]["desc"] = "프롬프트 초안 생성 중..."
    st.session_state["current_process"]["progress"] = 0.3
    result = coordinator.process_prompt_workflow(user_input, options, domain, mode='basic')
    if not isinstance(st.session_state.get("current_process"), dict):
        st.session_state["current_process"] = {}
    st.session_state["current_process"]["desc"] = "프롬프트 피드백/평가 중..."
    st.session_state["current_process"]["progress"] = 0.7
    # 결과 표시
    display_prompt_result(result, "기본")
    st.session_state["current_process"] = None

def process_advanced_prompt(user_input: str, domain: str, options: Dict[str, Any]):
    """심화 프롬프트 처리"""
    # 대시보드 연동: 프롬프트 생성 시작
    st.session_state["current_process"] = {"type": "prompt", "desc": "고급 프롬프트 생성 중...", "progress": 0.1}
    if not isinstance(st.session_state.get("current_process"), dict):
        st.session_state["current_process"] = {"type": "prompt", "desc": "고급 프롬프트 생성 중...", "progress": 0.1}
    coordinator = CoordinatorAgent()
    if not isinstance(st.session_state.get("current_process"), dict):
        st.session_state["current_process"] = {"type": "prompt", "desc": "고급 프롬프트 생성 중...", "progress": 0.1}
    st.session_state["current_process"]["desc"] = "고급 프롬프트 초안 생성 중..."
    st.session_state["current_process"]["progress"] = 0.3
    result = coordinator.process_prompt_workflow(user_input, options, domain, mode='advanced')
    if not isinstance(st.session_state.get("current_process"), dict):
        st.session_state["current_process"] = {"type": "prompt", "desc": "고급 프롬프트 생성 중...", "progress": 0.1}
    st.session_state["current_process"]["desc"] = "고급 프롬프트 피드백/평가 중..."
    st.session_state["current_process"]["progress"] = 0.7
    display_prompt_result(result, "심화")
    st.session_state["current_process"] = None

def display_prompt_result(result: Dict[str, Any], mode: str):
    """프롬프트 결과 표시"""
    
    st.success(f"{mode} 프롬프트 생성 완료!")
    
    # 결과를 세션 상태에 저장
    if "prompt_results" not in st.session_state:
        st.session_state.prompt_results = []
    
    import datetime
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    result_id = len(st.session_state.prompt_results)
    st.session_state.prompt_results.append({
        "id": result_id,
        "mode": mode,
        "result": result,
        "timestamp": current_time
    })
    
    # 탭으로 결과 표시 (최종 프롬프트, 생성 과정, 품질 평가, 결과 관리)
    tab1, tab2, tab3, tab4 = st.tabs(["최종 프롬프트", "생성 과정", "품질 평가", "결과 관리"])
    
    with tab1:
        display_final_prompt(result)
    
    with tab2:
        display_generation_process(result)
    
    with tab3:
        display_quality_assessment(result)
    
    with tab4:
        display_result_management(result_id, result)

def display_final_prompt(result: Dict[str, Any]):
    """최종 프롬프트 표시 (자동 개선본 강조)"""
    final_prompt = result.get('final_prompt', '')
    improved_prompt = result.get('improved_prompt', '')
    draft_prompt = result.get('draft_prompt', '')
    
    st.subheader("최종 프롬프트 (자동 개선본)")
    st.text_area(
        "최종 고품질 프롬프트 (자동 개선)",
        value=final_prompt,
        height=300,
        key="final_prompt_display",
        help="LLM이 모든 피드백을 반영해 자동 생성한 최종 프롬프트입니다."
    )
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("최종본 복사", key="copy_final_prompt"):
            try:
                pyperclip.copy(final_prompt)
                st.success("최종 프롬프트가 클립보드에 복사되었습니다!")
            except:
                st.error("복사에 실패했습니다. 수동으로 복사해주세요.")
    with col2:
        st.info("최종 프롬프트를 복사해 바로 활용하거나, 아래 초안/피드백/개선본과 비교해보세요.")
    st.divider()
    st.markdown("#### 개선 전/후 비교")
    st.markdown("**초안**")
    st.text_area("초안 프롬프트", value=draft_prompt, height=120, key="draft_prompt_display", disabled=True)
    st.markdown("**도메인/QA 피드백 반영 개선본**")
    st.text_area("개선본", value=improved_prompt, height=120, key="improved_prompt_display", disabled=True)

def display_generation_process(result: Dict[str, Any]):
    """생성 과정 표시"""
    
    st.subheader("프롬프트 생성 과정")
    
    # 1단계: 초안 생성
    with st.expander("프롬프트 엔지니어 - 초안 생성", expanded=True):
        draft_prompt = result.get('draft_prompt', '')
        rationale = result.get('engineer_rationale', '')
        
        st.markdown("**초안 프롬프트:**")
        st.text_area("", value=draft_prompt, height=200, disabled=True)
        
        st.markdown("**설계 근거:**")
        st.info(rationale)
    
    # 2단계: 도메인 피드백
    with st.expander("도메인 전문가 - 피드백 및 개선", expanded=True):
        feedback = result.get('domain_feedback', '')
        
        st.markdown("**도메인 전문가 피드백:**")
        st.info(feedback)
    
    # 3단계: QA 평가
    with st.expander("QA 평가자 - 품질 평가", expanded=True):
        score = result.get('qa_score', 0)
        review = result.get('qa_review', '')
        improvement = result.get('qa_improvement', '')
        
        # 점수 표시
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("품질 점수", f"{score}/100")
        
        with col2:
            if score >= 90:
                st.success("A등급 - 우수")
            elif score >= 80:
                st.info("B등급 - 양호")
            elif score >= 70:
                st.warning("C등급 - 보통")
            else:
                st.error("D등급 - 개선 필요")
        
        st.markdown("**상세 평가:**")
        st.info(review)
        
        st.markdown("**개선 제안:**")
        st.warning(improvement)

def display_quality_assessment(result: Dict[str, Any]):
    """품질 평가 상세 표시"""
    
    st.subheader("품질 평가 상세")
    
    score = result.get('qa_score', 0)
    review = result.get('qa_review', '')
    improvement = result.get('qa_improvement', '')
    
    # 점수 차트
    st.progress(score / 100)
    st.caption(f"전체 품질 점수: {score}/100")
    
    # 평가 세부사항
    st.markdown("### 평가 세부사항")
    st.text_area("평가 내용", value=review, height=250, disabled=True)
    
    # 개선 제안
    st.markdown("### 개선 제안")
    st.text_area("개선사항", value=improvement, height=200, disabled=True)
    
    # 등급별 색상 표시
    if score >= 90:
        st.success("A등급 - 우수한 품질의 프롬프트입니다!")
    elif score >= 80:
        st.info("B등급 - 양호한 품질의 프롬프트입니다.")
    elif score >= 70:
        st.warning("C등급 - 보통 품질입니다. 개선을 고려해보세요.")
    else:
        st.error("D등급 - 개선이 필요합니다.")

def display_result_management(result_id: int, result: Dict[str, Any]):
    """결과 관리 UI"""
    
    st.subheader("결과 관리")
    
    # 저장된 프롬프트 목록
    st.markdown("### 저장된 프롬프트")
    
    # 저장 기능
    col1, col2 = st.columns([1, 1])
    
    with col1:
        filename = st.text_input(
            "파일명",
            value=f"prompt_{result_id}",
            help="저장할 파일명을 입력하세요"
        )
        
        if st.button("저장", type="primary"):
            from tools.prompt_tool.core import save_prompt_to_file
            filepath = save_prompt_to_file(result, f"{filename}.json")
            if filepath:
                st.success(f"프롬프트가 저장되었습니다: {filepath}")
            else:
                st.error("저장에 실패했습니다.")
    
    with col2:
        # 저장된 파일 목록
        from tools.prompt_tool.core import list_saved_prompts
        saved_files = list_saved_prompts()
        
        if saved_files:
            st.markdown("**저장된 파일 목록:**")
            for file in saved_files[:5]:  # 최근 5개만 표시
                st.text(f"{file}")
        else:
            st.info("저장된 프롬프트가 없습니다.")
    
    # 프롬프트 수정
    st.markdown("### 프롬프트 수정")
    
    current_prompt = result.get('improved_prompt', result.get('draft_prompt', ''))
    modified_prompt = st.text_area(
        "프롬프트 수정",
        value=current_prompt,
        height=250,
        help="프롬프트를 수정하고 '업데이트' 버튼을 눌러 결과를 반영하세요"
    )
    
    if st.button("업데이트"):
        # 수정된 프롬프트로 결과 업데이트
        result['improved_prompt'] = modified_prompt
        st.session_state.prompt_results[result_id]['result'] = result
        st.success("프롬프트가 업데이트되었습니다!")
        st.rerun()

def render_prompt_history():
    """프롬프트 히스토리 표시"""
    
    if "prompt_results" in st.session_state and st.session_state.prompt_results:
        st.subheader("프롬프트 히스토리")
        
        for i, prompt_data in enumerate(st.session_state.prompt_results):
            with st.expander(f"{prompt_data['mode']} 모드 - {prompt_data['timestamp']}", expanded=False):
                result = prompt_data['result']
                final_prompt = result.get('improved_prompt', result.get('draft_prompt', ''))
                
                st.text_area(f"프롬프트 {i+1}", value=final_prompt, height=150, disabled=True)
                
                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    st.metric("품질 점수", f"{result.get('qa_score', 0)}/100")
                with col2:
                    if st.button("복사", key=f"copy_history_{i}"):
                        try:
                            pyperclip.copy(final_prompt)
                            st.success("복사됨!")
                        except:
                            st.error("복사 실패")
                with col3:
                    if st.button("삭제", key=f"delete_history_{i}"):
                        del st.session_state.prompt_results[i]
                        st.rerun() 