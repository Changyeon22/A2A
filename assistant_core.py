# assistant_core.py

import os
import json
import importlib.util
import sys
from dotenv import load_dotenv

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

loaded_tools_schemas = [] # LLM에게 전달할 모든 도구의 스키마 목록
loaded_tool_functions = {} # LLM이 호출할 함수 이름과 실제 파이썬 함수 매핑

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
    def validate_tool_module(module):
        """기본 도구 모듈 검증 함수"""
        has_schemas = hasattr(module, 'TOOL_SCHEMAS') and isinstance(module.TOOL_SCHEMAS, list)
        has_tool_map = hasattr(module, 'TOOL_MAP') and isinstance(module.TOOL_MAP, dict)
        return has_schemas and has_tool_map

# 어시스턴트가 사용할 도구 모듈 리스트
# tools 폴더를 스캔하여 동적으로 로드합니다.
tool_modules_to_load = []

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

def load_tools_from_directory(directory: str) -> tuple:
    """
    지정된 디렉토리에서 모든 도구 스키마와 함수를 동적으로 로드합니다.
    
    각 도구 모듈(core.py)은 표준 인터페이스를 준수하는지 검증하고,
    검증에 실패한 모듈은 로드하지 않습니다.
    
    Args:
        directory (str): 도구 디렉토리의 절대 경로
        
    Returns:
        tuple: (모든 도구 스키마 목록, 함수 이름과 구현의 매핑 딕셔너리)
    """
    all_schemas = []
    all_tool_maps = {}
    exclude_dirs = set(['__pycache__', 'tool_template'])  # 제외할 디렉토리 목록

    for tool_name in os.listdir(directory):
        tool_path = os.path.join(directory, tool_name)
        if os.path.isdir(tool_path) and tool_name not in exclude_dirs:
            core_module_path = os.path.join(tool_path, "core.py")
            if os.path.exists(core_module_path):
                module_name = f"tools.{tool_name}.core"
                try:
                    # 이전에 로드된 모듈이 있다면 리로드
                    if module_name in sys.modules:
                        module = importlib.reload(sys.modules[module_name])
                    else:
                        module = importlib.import_module(module_name)
                    
                    print(f"[Tool Discovery] 도구 모듈 로드 중: {module_name}")
                    
                    # 모듈 검증
                    is_valid = validate_tool_module(module)
                    if not is_valid:
                        print(f"[Tool Validation] 경고: {module_name} 모듈이 도구 인터페이스를 준수하지 않습니다. 이 모듈은 로드되지 않습니다.")
                        continue

                    schemas = getattr(module, 'TOOL_SCHEMAS', None)
                    tool_map = getattr(module, 'TOOL_MAP', None)

                    # 스키마 로드
                    if schemas and isinstance(schemas, list):
                        # 정보 로깅을 위해 도구 이름 추출
                        tool_names = [schema.get('function', {}).get('name', 'unknown') 
                                      for schema in schemas if 'function' in schema]
                        tool_names_str = ", ".join(tool_names)
                        
                        all_schemas.extend(schemas)
                        print(f"  - {tool_name}.core에서 {len(schemas)}개 도구 스키마 로드: {tool_names_str}")
                    else:
                        print(f"[Tool Load] 경고: {tool_name}.core에서 유효한 'TOOL_SCHEMAS' 리스트를 찾을 수 없습니다.")
                        continue

                    # 함수 매핑 로드
                    if tool_map and isinstance(tool_map, dict):
                        # 함수 이름과 모듈 정보를 함께 기록하여 디버깅에 도움이 되도록 함
                        for func_name, func in tool_map.items():
                            if func_name in all_tool_maps:
                                print(f"[Tool Load] 경고: '{func_name}' 함수가 이미 로드되어 있습니다. {tool_name}.core의 구현으로 덮어씌웁니다.")
                            all_tool_maps[func_name] = func
                            
                        print(f"  - {tool_name}.core에서 {len(tool_map)}개 함수 로드: {', '.join(tool_map.keys())}")
                    else:
                        print(f"[Tool Load] 경고: {tool_name}.core에서 유효한 'TOOL_MAP' 딕셔너리를 찾을 수 없습니다.")
                        continue

                    # 스키마와 함수 매핑의 일관성 검증
                    schema_function_names = set()
                    for schema in schemas:
                        if 'function' in schema:
                            function_name = schema['function'].get('name')
                            if function_name:
                                schema_function_names.add(function_name)
                    
                    tool_map_function_names = set(tool_map.keys())
                    
                    # 스키마에는 있지만 구현이 없는 함수 확인
                    missing_implementations = schema_function_names - tool_map_function_names
                    if missing_implementations:
                        print(f"[Tool Validation] 경고: {tool_name}.core에서 다음 함수들의 구현이 없습니다: {', '.join(missing_implementations)}")
                    
                    # 구현은 있지만 스키마가 없는 함수 확인
                    extra_implementations = tool_map_function_names - schema_function_names
                    if extra_implementations:
                        print(f"[Tool Validation] 정보: {tool_name}.core에서 다음 함수들은 스키마가 없습니다: {', '.join(extra_implementations)}")

                except ImportError as e:
                    print(f"[Tool Load] 오류: 모듈 {module_name}를 가져올 수 없습니다. 오류: {e}")
                except Exception as e:
                    print(f"[Tool Load] 오류: {module_name} 모듈 로드 중 예상치 못한 오류 발생: {e}")
    
    print(f"[Tool Summary] 총 {len(all_schemas)}개 도구 스키마와 {len(all_tool_maps)}개 함수 매핑을 로드했습니다.")
    return all_schemas, all_tool_maps

loaded_tools_schemas, loaded_tool_functions = load_tools_from_directory(tools_abs_path)

# --- LLM을 통한 명령 처리 및 함수 호출 로직 (아래는 변경 없음) ---
def process_command_with_llm_and_tools(command_text: str, conversation_history: list) -> dict:
    if not command_text:
        return {"status": "error", "response": "명령을 받지 못했습니다."}

    # --- 시스템 프롬프트 정의 (프롬프트 튜닝/Agent 라우팅 강화) ---
    system_prompt = '''
너는 AI 비서이자 멀티에이전트 코디네이터야.  
사용자의 요청을 분석하여, 각 에이전트(Agent)와 도구(Tool)의 전문성을 최대한 활용해 최적의 결과를 만들어내.  
아래의 규칙과 절차를 반드시 준수해.

[1. 에이전트/도구 역할 및 책임]
- 각 에이전트/도구는 자신의 전문 영역에만 집중하여, 책임 범위 내에서만 결과를 생성해야 해.
- 복합 요청의 경우, 각 에이전트가 순차적 또는 병렬적으로 협업하여 중간 결과를 공유하고, 최종 통합 결과를 생성해.
- 필요하다면, 중간 결과를 다른 에이전트에게 전달하여 추가 분석/가공/확장 작업을 수행해.

[2. A2A 구조 및 협업 단계]
- (1) 요청 분석 → (2) 에이전트/도구 분배 → (3) 개별 실행 → (4) 중간 결과 취합 → (5) 통합/후처리 → (6) 최종 결과 생성
- 각 단계에서 수행한 작업, 사용한 도구, 중간 결과를 명확하게 기록(log)하고, 필요시 상세 근거와 출처를 남겨.
- 협업이 필요한 경우, 각 에이전트의 결과를 명확히 구분하여 통합하되, 중복/충돌/누락이 없도록 검증해.

[3. 결과물 품질 및 사용자 맞춤화]
- 모든 답변은 신뢰성, 정확성, 최신성, 근거, 예시, 한계점, 참고자료(링크/출처) 등을 포함해야 해.
- 사용자의 요청 맥락(목적, 난이도, 톤, 길이, 포맷 등)을 파악하여, 맞춤형으로 결과물을 생성해.
- 복잡한 데이터/코드는 표, 코드블록, 시각화, 단계별 설명 등으로 명확하게 제시.
- 결과물의 한계나 불확실성이 있다면 반드시 명시하고, 추가 질문/확장 가능성도 안내해.
- 상세 답변(detailed_text)은 항상 JSON 형식으로 전달해야 하며, 표, 코드, 링크 등 다양한 포맷을 포함할 수 있다.

[4. 음성/텍스트 UX 및 인터랙션]
- speak_text 도구를 반드시 사용하여,  
  1) 음성(voice_text): 핵심 요약, 간결하고 명확하게  
  2) 상세(detailed_text): 전체 맥락, 근거, 예시, 코드, 링크, 참고자료 등 포함  
- speak_text의 speed, emotion 등 파라미터를 맥락에 맞게 조절(예: 축하, 경고, 안내 등)
- 모든 답변은 한국어로 제공

[5. 오류 복구 및 투명성]
- 에이전트/도구 실행 중 오류 발생 시,  
  1) 오류 원인과 위치를 명확히 설명  
  2) 자동 복구/재시도 절차를 안내  
  3) 사용자가 직접 조치할 수 있는 방법도 제시  
- 모든 과정(분배, 실행, 통합, 오류 등)은 투명하게 기록(log)하여, 추후 감사/디버깅이 가능하도록 해.

[6. 예시]
- "2023년 매출 데이터로 트렌드 차트 그려줘"  
  → DataAnalysisTool에 분배, 결과 요약(음성) + 상세 차트/분석(텍스트, 근거, 한계, 추가 질문 안내)
- "이메일 요약하고 답장도 작성해줘"  
  → EmailAgent에 요약 요청 → 요약 결과를 바탕으로 답장 생성 → 결과 통합 및 안내

[7. 절대적 규칙]
- speak_text 호출 없이 답변을 종료하지 마.
- 도구/에이전트 호출 및 협업 과정을 투명하게 기록(log)하고, 오류 발생 시 상세 원인과 해결 방안 제시.
- 사용자의 요구와 맥락을 항상 최우선으로 고려하여, 최고의 품질로 응답해.

(필요시, 각 에이전트/도구의 상세 역할, 예시, 포맷, 협업 시나리오 등을 추가로 명시할 수 있음)
'''

    # 대화 기록에 시스템 프롬프트 추가
    messages = [{"role": "system", "content": system_prompt}]
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
                            
                        # 음성 생성은 간결한 텍스트로만 수행
                        voice_args = {k: v for k, v in function_args.items() if k != "detailed_text"}
                        audio_bytes = function_to_call(**voice_args)
                        
                        return {
                            "status": "success",
                            "response_type": "audio_response", # 새로운 응답 타입
                            "voice_text": voice_text,  # 음성으로 전달되는 간결한 텍스트
                            "detailed_text": detailed_text,  # UI에 표시될 상세 텍스트
                            "audio_content": audio_bytes
                        }

                    # 다른 일반 도구들 처리
                    print(f"[Tool Call] Function: {function_name}, Args: {function_args}")
                    function_response = function_to_call(**function_args)
                    
                    # 바이너리 데이터 로깅 방지
                    if isinstance(function_response, bytes):
                        print(f"[Tool Response] {function_name} returned binary data of length: {len(function_response)} bytes")
                    else:
                        print(f"[Tool Response] {function_name} returned: {str(function_response)[:100]}{'...' if str(function_response) and len(str(function_response)) > 100 else ''}")

                    # 바이너리 데이터인 경우 안전한 방법으로 처리
                    content_value = "[Binary data]" if isinstance(function_response, bytes) else str(function_response)
                    
                    messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": content_value, # 함수 결과는 문자열로 변환 (바이너리는 안전하게 처리)
                        }
                    )
                # 도구 사용 결과를 바탕으로 LLM이 다시 생각하도록 루프 계속
                continue

            # 2. LLM이 도구 사용 없이 직접 답변을 생성한 경우 (Fallback)
            # LLM이 speak_text를 사용하라는 지시를 어긴 경우에 해당
            final_response_text = response_message.content
            print(f"[Fallback Response] LLM generated text directly: {final_response_text}")
            return {
                "status": "success",
                "response_type": "text_fallback",
                "text_content": final_response_text,
                "audio_content": None # 오디오 없음
            }
        
        except Exception as e:
            print(f"LLM 처리 중 오류 발생: {e}")
            return {"status": "error", "response": str(e)}

# --- 초기 설정 및 로드 (스크립트 로드 시 한 번만 실행) ---
GLOBAL_TOOLS_SCHEMAS = loaded_tools_schemas
GLOBAL_TOOL_FUNCTIONS = loaded_tool_functions

if not openai.api_key:
    raise RuntimeError("OpenAI API Key가 설정되지 않았습니다. '.env' 파일을 확인하세요.")

if not GLOBAL_TOOLS_SCHEMAS or not GLOBAL_TOOL_FUNCTIONS:
    print(f"ERROR: Final check failed. loaded_tools_schemas count: {len(loaded_tools_schemas)}, loaded_tool_functions count: {len(loaded_tool_functions)}")
    raise RuntimeError("도구 로드 실패. 'tools' 디렉토리 및 core.py 파일들을 확인하세요.")