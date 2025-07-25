"""
tool_template/core.py - 새 도구 개발을 위한 템플릿 파일

이 파일은 새로운 도구 개발 시 참고할 수 있는 템플릿입니다.
새 도구를 만들 때 이 파일을 복사하여 사용하세요.
"""

import sys
import os
from typing import Dict, List, Any, Optional, Union

# 상위 디렉토리 import를 위한 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from tool_interface import ToolInterface, validate_tool_module
except ImportError:
    # 개발 시 tool_interface.py가 없을 수 있으므로 대비
    class ToolInterface:
        pass
    
    def validate_tool_module(module):
        return True

# --- LLM이 사용할 도구 명세 (TOOL_SCHEMAS) ---
# OpenAI 함수 호출 스키마 형식을 따릅니다.
# https://platform.openai.com/docs/guides/function-calling
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "example_function",
            "description": "이 함수에 대한 명확한 설명을 작성하세요. LLM이 이 설명을 보고 함수를 호출할지 결정합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "문자열 매개변수에 대한 설명"
                    },
                    "param2": {
                        "type": "integer",
                        "description": "정수 매개변수에 대한 설명"
                    },
                    "param3": {
                        "type": "number",
                        "description": "실수 매개변수에 대한 설명"
                    },
                    "param4": {
                        "type": "boolean",
                        "description": "불리언 매개변수에 대한 설명"
                    },
                    "param5": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "문자열 배열 매개변수에 대한 설명"
                    },
                    "param6": {
                        "type": "object",
                        "properties": {
                            "nested_param": {
                                "type": "string"
                            }
                        },
                        "description": "객체 매개변수에 대한 설명"
                    }
                },
                "required": ["param1"]  # 필수 매개변수 목록
            }
        }
    }
    # 추가 도구가 필요한 경우 여기에 더 추가하세요
]


def example_function(param1: str, param2: int = 0, param3: float = 0.0,
                    param4: bool = False, param5: List[str] = None,
                    param6: Dict[str, Any] = None) -> Any:
    """
    도구 함수의 예시입니다. 이 주석은 개발자를 위한 것입니다.
    
    이 함수는 다양한 타입의 매개변수를 받아 처리하는 방법을 보여줍니다.
    실제 함수를 구현할 때는 이 템플릿을 참고하여 필요한 매개변수와 반환 타입을 정의하세요.
    
    Args:
        param1 (str): 필수 문자열 매개변수 설명
        param2 (int, optional): 선택적 정수 매개변수 설명. 기본값: 0
        param3 (float, optional): 선택적 실수 매개변수 설명. 기본값: 0.0
        param4 (bool, optional): 선택적 불리언 매개변수 설명. 기본값: False
        param5 (List[str], optional): 선택적 문자열 리스트 매개변수 설명. 기본값: None
        param6 (Dict[str, Any], optional): 선택적 객체 매개변수 설명. 기본값: None
    
    Returns:
        Any: 함수의 반환 타입과 값을 설명하세요
        
    Raises:
        ValueError: 매개변수 값이 유효하지 않은 경우
        Exception: 기타 예외가 발생할 수 있는 경우
    """
    # 매개변수 기본값 및 유효성 검사
    param5 = param5 or []
    param6 = param6 or {}
    
    # 유효성 검사 예시
    if not param1:
        raise ValueError("param1은 비어있을 수 없습니다")
    
    # 로깅 - 함수 호출 추적을 위해 모든 도구 함수에 추가하세요
    print(f"[example_tool] example_function 호출: param1={param1}, param2={param2}, "
          f"param3={param3}, param4={param4}, param5={param5}, param6={param6}")
    
    try:
        # 실제 함수 로직 구현
        result = f"예시 결과: {param1}"
        
        # 성공 로깅
        print(f"[example_tool] example_function 성공: {result}")
        return result
        
    except Exception as e:
        # 오류 로깅 - 항상 예외를 잡아 로깅하세요
        print(f"[example_tool] example_function 오류: {e}")
        raise  # 필요에 따라 예외를 다시 발생시키거나 처리하세요


# --- 도구 이름과 실제 함수를 매핑 (TOOL_MAP) ---
# TOOL_SCHEMAS에 정의된 모든 함수 이름이 여기에 매핑되어야 합니다.
TOOL_MAP = {
    "example_function": example_function,
}


# --- 모듈 유효성 검증 ---
if __name__ == "__main__":
    # 직접 모듈을 실행했을 때 유효성 테스트 실행
    is_valid = validate_tool_module(sys.modules[__name__])
    print(f"도구 템플릿 유효성 검증: {'성공' if is_valid else '실패'}")
    
    # 간단한 테스트 실행
    try:
        test_result = example_function("테스트")
        print(f"테스트 실행 결과: {test_result}")
    except Exception as e:
        print(f"테스트 실행 오류: {e}")
