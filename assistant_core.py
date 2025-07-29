# assistant_core.py

import os
import json
import importlib.util
import sys
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional, Tuple, Union

# tools 모듈 경로를 sys.path에 추가
current_script_dir = os.path.dirname(os.path.abspath(__file__))
tools_abs_path = os.path.join(current_script_dir, "tools")
if tools_abs_path not in sys.path:
    sys.path.insert(0, tools_abs_path)

import openai

# 환경 변수 로드
load_dotenv()
openai.api_key = os.environ.get("OPENAI_API_KEY")

# --- 도구(Tools) 동적 로딩 ---
TOOLS_ROOT_DIR = "tools"

loaded_tools_schemas: List[Dict[str, Any]] = [] # LLM에게 전달할 모든 도구의 스키마 목록
loaded_tool_functions: Dict[str, Any] = {} # LLM이 호출할 함수 이름과 실제 파이썬 함수 매핑

# 표준 도구 인터페이스 로드 시도
try:
    tool_interface_path = os.path.join(current_script_dir, TOOLS_ROOT_DIR, "tool_interface.py")
    if os.path.exists(tool_interface_path):
        sys.path.insert(0, os.path.join(current_script_dir, TOOLS_ROOT_DIR))
        try:
            from tool_interface import validate_tool_module
            print("[Tool Interface] 도구 검증 인터페이스를 로드했습니다.")
            VALIDATOR_AVAILABLE = True
        except ImportError:
            print("[Tool Interface] 도구 검증 인터페이스를 로드하는 데 실패했습니다. 기본 검증을 사용합니다.")
            VALIDATOR_AVAILABLE = False
    else:
        print("[Tool Interface] tool_interface.py를 찾을 수 없습니다. 기본 검증을 사용합니다.")
        VALIDATOR_AVAILABLE = False
except Exception as e:
    print(f"[Tool Interface] 도구 인터페이스 로드 중 오류 발생: {e}")
    VALIDATOR_AVAILABLE = False

# 기본 검증 함수 정의
if not VALIDATOR_AVAILABLE:
    def validate_tool_module(module: Any) -> bool:
        """기본 도구 모듈 검증 함수"""
        has_schemas = hasattr(module, 'TOOL_SCHEMAS') and isinstance(module.TOOL_SCHEMAS, list)
        has_tool_map = hasattr(module, 'TOOL_MAP') and isinstance(module.TOOL_MAP, dict)
        return has_schemas and has_tool_map

# 어시스턴트가 사용할 도구 모듈 리스트
# tools 폴더를 스캔하여 동적으로 로드합니다.
tool_modules_to_load: List[str] = []

tools_root_abs_path = os.path.join(current_script_dir, TOOLS_ROOT_DIR)
if os.path.exists(tools_root_abs_path):
    for tool_dir_name in os.listdir(tools_root_abs_path):
        tool_dir_path = os.path.join(tools_root_abs_path, tool_dir_name)
        # __pycache__ 같은 폴더는 무시하고, 실제 디렉토리인지 확인
        if os.path.isdir(tool_dir_path) and not tool_dir_name.startswith('__'):
            # tool_template은 실제 도구가 아니므로 로드하지 않음
            if tool_dir_name == "tool_template":
                continue
                
            core_file_path = os.path.join(tool_dir_path, 'core.py')
            if os.path.exists(core_file_path):
                module_path_str = f"{tool_dir_name}.core"
                tool_modules_to_load.append(module_path_str)
                print(f"[Tool Discovery] 도구 모듈 발견: {module_path_str}")

# --- 도구 동적 로딩 (import) ---
# 발견된 모듈들을 실제로 임포트하고, 스키마와 함수를 로드합니다.
if not tool_modules_to_load:
    print("WARNING: No tool modules found to load.")

def load_tools_from_directory(directory: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    지정된 디렉토리에서 모든 도구 스키마와 함수를 동적으로 로드합니다.
    
    각 도구 모듈(core.py)은 표준 인터페이스를 준수하는지 검증하고,
    검증에 실패한 모듈은 로드하지 않습니다.
    
    Args:
        directory (str): 도구 디렉토리의 절대 경로
        
    Returns:
        tuple: (모든 도구 스키마 목록, 함수 이름과 구현의 매핑 딕셔너리)
    """
    all_schemas: List[Dict[str, Any]] = []
    all_tool_maps: Dict[str, Any] = {}
    exclude_dirs = set(['__pycache__', 'tool_template'])  # 제외할 디렉토리 목록

    for tool_name in os.listdir(directory):
        tool_path = os.path.join(directory, tool_name)
        if os.path.isdir(tool_path) and tool_name not in exclude_dirs:
            core_module_path = os.path.join(tool_path, "core.py")
            if os.path.exists(core_module_path):
                try:
                    # 모듈 동적 로딩
                    spec = importlib.util.spec_from_file_location(f"{tool_name}.core", core_module_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # 모듈 검증
                        if validate_tool_module(module):
                            # 스키마와 함수 매핑 로드
                            if hasattr(module, 'TOOL_SCHEMAS'):
                                all_schemas.extend(module.TOOL_SCHEMAS)
                                print(f"[Tool Load] {tool_name} 스키마 로드 완료: {len(module.TOOL_SCHEMAS)}개")
                            
                            if hasattr(module, 'TOOL_MAP'):
                                all_tool_maps.update(module.TOOL_MAP)
                                print(f"[Tool Load] {tool_name} 함수 매핑 로드 완료: {len(module.TOOL_MAP)}개")
                        else:
                            print(f"[Tool Load] {tool_name} 모듈 검증 실패 - 로드 건너뜀")
                            
                except Exception as e:
                    print(f"[Tool Load] {tool_name} 모듈 로드 실패: {e}")
                    continue
    
    print(f"[Tool Summary] 총 {len(all_schemas)}개 도구 스키마와 {len(all_tool_maps)}개 함수 매핑을 로드했습니다.")
    return all_schemas, all_tool_maps

loaded_tools_schemas, loaded_tool_functions = load_tools_from_directory(tools_abs_path)

# --- LLM을 통한 명령 처리 및 함수 호출 로직 ---
def process_command_with_llm_and_tools(command_text: str, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    LLM과 도구를 사용하여 사용자 명령을 처리합니다.
    
    Args:
        command_text (str): 사용자 입력 텍스트
        conversation_history (List[Dict[str, str]]): 대화 히스토리
        
    Returns:
        Dict[str, Any]: 처리 결과
    """
    if not command_text:
        return {"status": "error", "response": "명령을 받지 못했습니다."}

    # --- 시스템 프롬프트 정의 (IT 실무자 특화 범용 프롬프트) ---
    system_prompt = '''
너는 IT 회사 실무자를 위한 AI 비서이자 멀티에이전트 코디네이터야.
개발자, 기획자, 디자이너, 마케터, PM 등 모든 IT 실무자의 업무를 지원해.
사용자의 요청을 분석하여, 각 에이전트(Agent)와 도구(Tool)의 전문성을 최대한 활용해 최적의 결과를 만들어내.
아래의 규칙과 절차를 반드시 준수해.

[1. IT 실무 도메인별 라우팅 및 책임]
- 각 에이전트/도구는 자신의 전문 영역에만 집중하여, 책임 범위 내에서만 결과를 생성해야 해.
- 복합 요청의 경우, 각 에이전트가 순차적 또는 병렬적으로 협업하여 중간 결과를 공유하고, 최종 통합 결과를 생성해.
- 필요하다면, 중간 결과를 다른 에이전트에게 전달하여 추가 분석/가공/확장 작업을 수행해.

[2. IT 실무 포지션별 최적화 라우팅]
- 개발자 요청: 코드 리뷰, 기술 문서, 시스템 설계 → ResearchAgent, DocumentWriterAgent, DataAnalysisTool
- 기획자 요청: 요구사항 분석, 기획서 작성, 프로젝트 관리 → PlanningTool, DocumentWriterAgent, ResearchAgent
- 디자이너 요청: UI/UX 설계, 프로토타입, 디자인 시스템 → ResearchAgent, DocumentWriterAgent, PlanningTool
- 마케터 요청: 콘텐츠 제작, 데이터 분석, 캠페인 기획 → DataAnalysisTool, EmailAgent, PlanningTool
- PM 요청: 프로젝트 관리, 일정 조율, 리스크 관리 → PlanningTool, EmailAgent, ResearchAgent
- 공통 요청: 이메일 처리, 음성 변환, 문서 요약 → EmailAgent, VoiceAgent, SummarizationTool

[3. A2A 구조 및 협업 단계]
- (1) 요청 분석 → (2) IT 실무 도메인 식별 → (3) 에이전트/도구 분배 → (4) 개별 실행 → (5) 중간 결과 취합 → (6) 통합/후처리 → (7) 최종 결과 생성
- 각 단계에서 수행한 작업, 사용한 도구, 중간 결과를 명확하게 기록(log)하고, 필요시 상세 근거와 출처를 남겨.
- 협업이 필요한 경우, 각 에이전트의 결과를 명확히 구분하여 통합하되, 중복/충돌/누락이 없도록 검증해.

[4. IT 실무 품질 기준 및 사용자 맞춤화]
- 모든 답변은 신뢰성, 정확성, 최신성, 근거, 예시, 한계점, 참고자료(링크/출처) 등을 포함해야 해.
- 기술적 정확성: 코드, 아키텍처, 기술 스택의 정확성과 최신 트렌드 반영
- 실무 적용성: 실제 업무에 바로 적용 가능한 수준의 구체성과 실용성
- 협업 친화성: 팀원 간 소통과 협업을 고려한 명확하고 이해하기 쉬운 결과물
- 확장성: 미래 요구사항 변화를 고려한 유연하고 확장 가능한 설계
- 사용자의 요청 맥락(목적, 난이도, 톤, 길이, 포맷 등)을 파악하여, 맞춤형으로 결과물을 생성해.
- 복잡한 데이터/코드는 표, 코드블록, 시각화, 단계별 설명 등으로 명확하게 제시.
- 결과물의 한계나 불확실성이 있다면 반드시 명시하고, 추가 질문/확장 가능성도 안내해.
- 상세 답변(detailed_text)은 항상 JSON 형식으로 전달해야 하며, 표, 코드, 링크 등 다양한 포맷을 포함할 수 있다.

[5. IT 실무 워크플로우 최적화]
- 개발 워크플로우: 요구사항 분석 → 설계 → 구현 → 테스트 → 배포 → 모니터링
- 기획 워크플로우: 시장 조사 → 요구사항 정의 → 기획서 작성 → 검토 → 승인
- 디자인 워크플로우: 사용자 조사 → 와이어프레임 → 프로토타입 → 디자인 시스템 → 검증
- 마케팅 워크플로우: 데이터 분석 → 전략 수립 → 콘텐츠 제작 → 실행 → 성과 측정
- 프로젝트 관리 워크플로우: 계획 수립 → 팀 구성 → 실행 → 모니터링 → 마무리

[6. 음성/텍스트 UX 및 인터랙션]
- speak_text 도구를 반드시 사용하여,  
  1) 음성(voice_text): 핵심 요약, 간결하고 명확하게  
  2) 상세(detailed_text): 전체 맥락, 근거, 예시, 코드, 링크, 참고자료 등 포함  
- speak_text의 speed, emotion 등 파라미터를 맥락에 맞게 조절(예: 축하, 경고, 안내 등)
- 모든 답변은 한국어로 제공

[7. 오류 복구 및 투명성]
- 에이전트/도구 실행 중 오류 발생 시,  
  1) 오류 원인과 위치를 명확히 설명  
  2) 자동 복구/재시도 절차를 안내  
  3) 사용자가 직접 조치할 수 있는 방법도 제시  
- 모든 과정(분배, 실행, 통합, 오류 등)은 투명하게 기록(log)하여, 추후 감사/디버깅이 가능하도록 해.

[8. IT 실무 예시]
- "새로운 웹 서비스 기획서 작성해줘"  
  → PlanningTool에 분배, 시장 조사 → 기획서 작성 → 검토 → 최종 결과(음성 요약 + 상세 문서)
- "코드 리뷰하고 개선점 제안해줘"  
  → ResearchAgent에 분배, 코드 분석 → 개선점 도출 → DocumentWriterAgent로 문서화 → 결과 통합
- "팀 회의록 요약하고 액션 아이템 정리해줘"  
  → SummarizationTool로 요약 → EmailAgent로 액션 아이템 추출 → 결과 통합 및 안내
- "마케팅 데이터 분석해서 인사이트 도출해줘"  
  → DataAnalysisTool로 분석 → 차트 생성 → 인사이트 도출 → 결과 시각화 및 설명

[9. 절대적 규칙]
- speak_text 호출 없이 답변을 종료하지 마.
- 도구/에이전트 호출 및 협업 과정을 투명하게 기록(log)하고, 오류 발생 시 상세 원인과 해결 방안 제시.
- 사용자의 요구와 맥락을 항상 최우선으로 고려하여, 최고의 품질로 응답해.
- IT 실무자의 업무 효율성과 생산성 향상을 최우선 목표로 삼아.

(필요시, 각 에이전트/도구의 상세 역할, 예시, 포맷, 협업 시나리오 등을 추가로 명시할 수 있음)
'''

    # 대화 기록에 시스템 프롬프트 추가
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    # 이전 대화 기록(시스템 프롬프트 제외) 추가
    messages.extend([msg for msg in conversation_history if msg['role'] != 'system'])
    # 현재 사용자 입력 추가
    messages.append({"role": "user", "content": command_text})

    # --- LLM과의 대화 및 도구 사용 루프 ---
    while True:
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=loaded_tools_schemas,
                tool_choice="auto",
            )
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            # 1. LLM이 도구 사용을 결정한 경우
            if tool_calls:
                messages.append(response_message) # LLM의 도구 호출 결정도 대화 기록에 추가

                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_to_call = loaded_tool_functions.get(function_name)
                    function_args = json.loads(tool_call.function.arguments)

                    # ** A2A 핵심 로직: speak_text 도구 특별 처리 **
                    if function_name == "speak_text":
                        print(f"[A2A Final Response] LLM decided to speak. Speed: {function_args.get('speed', 1.0)}")
                        # 음성 답변(간결)과 상세 답변 분리
                        voice_text = function_args.get("text", "")
                        detailed_text = function_args.get("detailed_text", "")
                        
                        # 상세 답변이 없는 경우 음성 답변을 상세 답변으로 사용
                        if not detailed_text:
                            detailed_text = voice_text
                        
                        # 음성 합성 실행
                        try:
                            audio_content = function_to_call(**function_args)
                            print(f"[A2A Audio] 음성 합성 완료: {len(audio_content) if audio_content else 0} bytes")
                            
                            # 최종 응답 반환
                            return {
                                "status": "success",
                                "response_type": "audio_response",
                                "voice_text": voice_text,
                                "detailed_text": detailed_text,
                                "audio_content": audio_content
                            }
                        except Exception as e:
                            print(f"[A2A Audio Error] 음성 합성 실패: {e}")
                            # 음성 합성 실패 시 텍스트 응답으로 폴백
                            return {
                                "status": "success",
                                "response_type": "text_fallback",
                                "text_content": detailed_text or voice_text
                            }
                    
                    # 2. 다른 도구들 실행
                    else:
                        print(f"[Tool Call] {function_name} 실행 중...")
                        try:
                            function_response = function_to_call(**function_args)
                            print(f"[Tool Result] {function_name} 결과: {function_response}")
                            
                            # 도구 실행 결과를 대화 기록에 추가
                            messages.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": str(function_response)
                            })
                        except Exception as e:
                            print(f"[Tool Error] {function_name} 실행 실패: {e}")
                            # 도구 실행 실패 시 오류 메시지를 대화 기록에 추가
                            messages.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": f"오류 발생: {str(e)}"
                            })

            # 2. LLM이 최종 응답을 생성한 경우
            else:
                print(f"[A2A Final Response] LLM 최종 응답: {response_message.content}")
                return {
                    "status": "success",
                    "response_type": "text_fallback",
                    "text_content": response_message.content
                }

        except Exception as e:
            print(f"[A2A Error] LLM 처리 중 오류: {e}")
            return {
                "status": "error",
                "response": f"처리 중 오류가 발생했습니다: {str(e)}"
            }

def get_loaded_tools_info() -> Dict[str, Any]:
    """
    로드된 도구 정보를 반환합니다.
    
    Returns:
        Dict[str, Any]: 도구 정보 딕셔너리
    """
    return {
        "schemas_count": len(loaded_tools_schemas),
        "functions_count": len(loaded_tool_functions),
        "available_functions": list(loaded_tool_functions.keys()),
        "schemas": loaded_tools_schemas
    }

def reload_tools() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    도구를 다시 로드합니다.
    
    Returns:
        Tuple[List[Dict[str, Any]], Dict[str, Any]]: 로드된 스키마와 함수 매핑
    """
    global loaded_tools_schemas, loaded_tool_functions
    loaded_tools_schemas, loaded_tool_functions = load_tools_from_directory(tools_abs_path)
    return loaded_tools_schemas, loaded_tool_functions