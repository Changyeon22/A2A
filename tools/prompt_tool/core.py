# tools/prompt_tool/core.py
"""
A2A 구조 기반 프롬프트 자동화 도구 모듈
- 역할별 프롬프트 생성/리라이팅/피드백/평가 함수 정의
"""
import os
import json
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

# OpenAI 클라이언트 초기화
def get_openai_client():
    """OpenAI 클라이언트 반환"""
    try:
        from openai import OpenAI
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not found")
            return None
        return OpenAI(api_key=api_key)
    except ImportError:
        logger.warning("OpenAI library not available")
        return None

# 프롬프트 엔지니어 역할: 고퀄리티 프롬프트 생성
def generate_high_quality_prompt(user_input: str, options: Dict[str, Any], mode: str = 'basic') -> Dict[str, Any]:
    """
    사용자의 요구사항과 옵션을 바탕으로 고퀄리티 프롬프트 초안을 생성한다.
    mode: 'basic' 또는 'advanced'에 따라 페르소나/시스템 프롬프트가 달라짐
    Returns: { 'prompt': str, 'rationale': str }
    """
    client = get_openai_client()
    if not client:
        return {
            'prompt': f"[고퀄리티 프롬프트] {user_input} (옵션: {options})",
            'rationale': "OpenAI 연동 미설정으로 인한 기본 응답"
        }
    
    # --- 페르소나별 시스템 프롬프트 ---
    if mode == 'advanced':
        system_prompt = '''당신은 “프롬프트 설계 아키텍트”입니다.

당신의 임무는, 사용자가 입력한 상세 목적/요구/옵션 등 디테일한 요구사항을 바탕으로,
**LLM 챗봇에게 입력할 수 있는, 고도화되고 구조화된 프롬프트 문장(질문/지시문)을** 만들어주는 것입니다.

- 사용자가 작성한 디테일한 요청과 선택 옵션을 바탕으로 chatGPT에게 가장 효과적인 프롬프트를 만들어내세요.
- 프롬프트에는 [페르소나], [맥락/배경], [핵심 과업 및 목표], [단계별 지침], [제약 조건], [Few-shot 예시], [출력 형식] 등 명세의 주요 요소가 자연스럽게 녹아들어야 합니다.
- 예시:  
  - 입력: 목적=데이터 분석 보고서 요약, 옵션: 대상=경영진, 출력=마크다운, 제약=500자 이내  
  - 출력: “아래 데이터 분석 보고서를 경영진이 빠르게 이해할 수 있도록 500자 이내로 요약해줘. 주요 인사이트와 수치 데이터를 강조해서 마크다운 형식으로 작성해줘.”

전문가의 상세 명세를 분석하여, LLM 챗봇에게 입력할 수 있는 최적의 프롬프트를 생성하세요.'''
        user_message = f"""
        상세 명세서(JSON):
        {json.dumps(options, ensure_ascii=False, indent=2)}
        
        사용자 요청:
        {user_input}
        
        위 정보를 바탕으로 위 시스템 프롬프트의 지침에 따라 최적의 프롬프트를 설계하세요.
        """
    else:
        system_prompt = '''당신은 “프롬프트 변환 전문가”입니다.

당신의 임무는, 초보자 또는 비전문 사용자가 일상 언어로 입력한 요청(예: “회의록 요약”, “이메일 작성”, “코드 리뷰”)과 선택 옵션을 바탕으로,
**LLM 챗봇에게 바로 입력할 수 있는, 명확하고 효과적인 프롬프트 문장(질문/지시문)을** 만들어주는 것입니다.

- 사용자가 작성한 간단한 요청과 선택 옵션을 바탕으로 chatGPT에게 가장 효과적인 프롬프트를 만들어내세요.
- 프롬프트 문장에는 사용자의 목적, 옵션(톤, 도메인, 출력 형식 등)이 자연스럽게, 하지만 반드시 반영되어야 합니다.
- 예시:  
  - 입력: “회의록 요약”, 옵션: 도메인=비즈니스, 톤=간결한, 출력=일반 텍스트  
  - 출력: “아래 회의록을 간결한 톤으로 3문장 이내로 요약해줘. 비즈니스 관점에서 핵심 결정사항을 강조해서 일반 텍스트로 작성해줘.”

사용자 입력과 옵션을 분석하여, LLM 챗봇에게 입력할 수 있는 최적의 프롬프트를 생성하세요.'''
        user_message = f"""
        사용자 요청:
        {user_input}
        
        선택된 옵션:
        {json.dumps(options, ensure_ascii=False, indent=2)}
        
        위 정보를 바탕으로 위 시스템 프롬프트의 지침에 따라 최적의 프롬프트를 설계하세요.
        """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=2000,
            temperature=0.7
        )

        result = response.choices[0].message.content.strip()
        return {
            'prompt': result,
            'rationale': f"{mode} persona prompt applied"
        }
        
    except Exception as e:
        logger.error(f"프롬프트 생성 중 오류: {e}")
        return {
            'prompt': f"[고퀄리티 프롬프트] {user_input} (옵션: {options})",
            'rationale': f"오류로 인한 기본 응답: {str(e)}"
        }

# 도메인 전문가 역할: 도메인 특화 피드백/보완
def domain_expert_feedback(prompt: str, domain: str) -> Dict[str, Any]:
    """
    도메인 전문가 관점에서 프롬프트를 평가/보완한다.
    Returns: { 'feedback': str, 'suggested_prompt': str }
    """
    client = get_openai_client()
    if not client:
        return {
            'feedback': f"[{domain} 전문가 피드백] OpenAI 연동 미설정",
            'suggested_prompt': prompt
        }
    
    try:
        # 도메인별 전문가 페르소나
        domain_personas = {
            "마케팅": "마케팅 전문가로서 브랜드 메시지, 타겟 오디언스, 콘텐츠 전략에 특화",
            "개발": "소프트웨어 개발 전문가로서 기술적 명확성, 코드 품질, 아키텍처 관점에 특화",
            "디자인": "UX/UI 디자인 전문가로서 사용자 경험, 시각적 일관성, 접근성에 특화",
            "교육": "교육 전문가로서 학습 목표, 평가 기준, 학습자 수준에 특화",
            "비즈니스": "비즈니스 전략 전문가로서 ROI, 시장 분석, 경쟁 우위에 특화"
        }
        
        persona = domain_personas.get(domain, "일반 전문가")
        
        system_prompt = f"""당신은 {domain} 분야의 전문가입니다. {persona}입니다.
        
        주어진 프롬프트를 {domain} 관점에서 평가하고 개선점을 제안해주세요.
        
        평가 기준:
        1. 도메인 적합성: {domain} 분야에 적합한 용어와 개념 사용
        2. 전문성: 도메인 전문가 수준의 깊이 있는 내용
        3. 실용성: 실제 업무에 바로 적용 가능한 수준
        4. 완성도: 누락된 중요한 요소가 없는지 확인
        
        응답 형식:
        - 피드백: 구체적인 평가와 개선점
        - 개선된 프롬프트: 수정된 프롬프트 텍스트"""

        user_message = f"""
        도메인: {domain}
        
        현재 프롬프트:
        {prompt}
        
        위 프롬프트를 {domain} 전문가 관점에서 평가하고 개선해주세요.
        """

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=1500,
            temperature=0.6
        )

        result = response.choices[0].message.content.strip()
        
        # 피드백과 개선된 프롬프트 분리
        if "피드백:" in result and "개선된 프롬프트:" in result:
            parts = result.split("개선된 프롬프트:")
            feedback_part = parts[0].replace("피드백:", "").strip()
            improved_part = parts[1].strip()
        else:
            feedback_part = result
            improved_part = prompt

        return {
            'feedback': feedback_part,
            'suggested_prompt': improved_part
        }
        
    except Exception as e:
        logger.error(f"도메인 피드백 생성 중 오류: {e}")
        return {
            'feedback': f"[{domain} 전문가 피드백] 오류로 인한 기본 응답: {str(e)}",
            'suggested_prompt': prompt
        }

# QA 평가자 역할: 품질 평가/점수화/개선점 제안
def qa_evaluate_prompt(prompt: str) -> Dict[str, Any]:
    """
    프롬프트의 명확성, 구체성, LLM 적합성 등 품질 평가 및 개선점 제안
    Returns: { 'score': int, 'review': str, 'improvement': str }
    """
    client = get_openai_client()
    if not client:
        return {
            'score': 80,
            'review': "OpenAI 연동 미설정으로 인한 기본 평가",
            'improvement': "OpenAI API 키 설정 후 재평가 필요"
        }
    
    try:
        system_prompt = """당신은 프롬프트 품질 평가 전문가입니다. 
        주어진 프롬프트의 품질을 종합적으로 평가해주세요.
        
        평가 기준 (각 항목 20점 만점):
        1. 명확성: 목적과 요구사항이 명확한가?
        2. 구체성: 구체적인 지시사항과 예시가 포함되어 있는가?
        3. 구조화: 논리적으로 구조화되어 있는가?
        4. 맥락 제공: 필요한 배경 정보가 충분한가?
        5. 출력 형식: 원하는 출력 형식이 명시되어 있는가?
        
        총점: 100점 만점
        등급: 90-100점(A), 80-89점(B), 70-79점(C), 60-69점(D), 60점 미만(F)
        
        응답 형식:
        - 점수: 숫자 (0-100)
        - 평가: 상세한 평가 내용
        - 개선점: 구체적인 개선 제안"""

        user_message = f"""
        평가할 프롬프트:
        {prompt}
        
        위 프롬프트를 품질 평가 기준에 따라 평가해주세요.
        """

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=1000,
            temperature=0.5
        )

        result = response.choices[0].message.content.strip()
        
        # 점수, 평가, 개선점 분리
        score = 80  # 기본값
        review = result
        improvement = "평가 결과를 확인해주세요."
        
        if "점수:" in result:
            try:
                score_text = result.split("점수:")[1].split("\n")[0].strip()
                score = int(score_text)
            except:
                pass
        
        if "평가:" in result and "개선점:" in result:
            parts = result.split("개선점:")
            review_part = parts[0].split("평가:")[1].strip()
            improvement_part = parts[1].strip()
            review = review_part
            improvement = improvement_part

        return {
            'score': score,
            'review': review,
            'improvement': improvement
        }
        
    except Exception as e:
        logger.error(f"QA 평가 중 오류: {e}")
        return {
            'score': 80,
            'review': f"오류로 인한 기본 평가: {str(e)}",
            'improvement': "오류 해결 후 재평가 필요"
        }

# 프롬프트 저장/로드 기능
def save_prompt_to_file(prompt_data: Dict[str, Any], filename: str = None) -> str:
    """프롬프트를 파일로 저장"""
    if not filename:
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"prompt_{timestamp}.json"
    
    # prompts 디렉토리 생성
    prompts_dir = "prompts"
    os.makedirs(prompts_dir, exist_ok=True)
    
    filepath = os.path.join(prompts_dir, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(prompt_data, f, ensure_ascii=False, indent=2)
        return filepath
    except Exception as e:
        logger.error(f"프롬프트 저장 중 오류: {e}")
        return ""

def load_prompt_from_file(filepath: str) -> Dict[str, Any]:
    """파일에서 프롬프트 로드"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"프롬프트 로드 중 오류: {e}")
        return {}

def list_saved_prompts() -> List[str]:
    """저장된 프롬프트 파일 목록 반환"""
    prompts_dir = "prompts"
    if not os.path.exists(prompts_dir):
        return []
    
    try:
        files = [f for f in os.listdir(prompts_dir) if f.endswith('.json')]
        return sorted(files, reverse=True)  # 최신 파일부터
    except Exception as e:
        logger.error(f"프롬프트 목록 조회 중 오류: {e}")
        return [] 