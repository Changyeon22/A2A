"""
도구(Tool) 모듈이 따라야 할 표준 인터페이스 정의

이 파일은 모든 도구 모듈이 구현해야 하는 표준 인터페이스를 정의합니다.
새로운 도구를 개발할 때 이 인터페이스를 참고하여 일관된 구조를 유지하세요.
"""

import json
from typing import Dict, List, Any, Callable


class ToolInterface:
    """
    도구 모듈이 구현해야 하는 표준 인터페이스
    
    모든 도구 모듈의 core.py는 이 인터페이스에 정의된 상수와 메서드를 제공해야 합니다.
    """
    
    # 도구 스키마 예시 (실제 구현 시 오버라이드)
    TOOL_SCHEMAS = [
        {
            "type": "function",
            "function": {
                "name": "example_function",
                "description": "이 함수의 목적과 기능에 대한 설명",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {
                            "type": "string",
                            "description": "파라미터 1에 대한 설명"
                        },
                        "param2": {
                            "type": "integer",
                            "description": "파라미터 2에 대한 설명"
                        }
                    },
                    "required": ["param1"]
                }
            }
        }
    ]
    
    # 도구 함수 매핑 예시 (실제 구현 시 오버라이드)
    TOOL_MAP = {
        "example_function": lambda param1, param2=None: f"param1: {param1}, param2: {param2}"
    }
    
    @staticmethod
    def validate_schema(schemas: List[Dict], tool_map: Dict[str, Callable]) -> bool:
        """
        도구 스키마와 함수 매핑의 유효성을 검증합니다.
        
        Args:
            schemas: 도구 스키마 목록
            tool_map: 함수 이름과 실제 함수의 매핑
            
        Returns:
            bool: 유효성 검증 결과 (True: 유효, False: 유효하지 않음)
        """
        try:
            # 1. 모든 스키마가 필요한 필드를 가지고 있는지 확인
            schema_function_names = []
            
            for schema in schemas:
                # OpenAI 표준 형식 확인: {"type": "function", "function": {"name": ...}}
                if schema.get("type") == "function" and "function" in schema:
                    function = schema.get("function", {})
                    if not function.get("name"):
                        print("Error: Function schema must have a name")
                        return False
                    schema_function_names.append(function["name"])
                
                # 기존 형식 확인: {"name": ..., "description": ..., "function": callable}
                elif "name" in schema and "function" in schema:
                    if not schema.get("name"):
                        print("Error: Legacy schema must have a name")
                        return False
                    schema_function_names.append(schema["name"])
                
                else:
                    print(f"Error: Invalid schema format. Schema must be either OpenAI format (with type='function') or legacy format (with 'name' field). Got: {schema}")
                    return False
                 
            # 2. 모든 스키마의 함수 이름이 tool_map에 있는지 확인
            for name in schema_function_names:
                if name not in tool_map:
                    print(f"Error: Function '{name}' defined in schema but not in tool_map")
                    return False
            
            # 3. tool_map에 있는 모든 함수가 스키마에 정의되어 있는지 확인
            for name in tool_map:
                if name not in schema_function_names:
                    print(f"Error: Function '{name}' defined in tool_map but not in schema")
                    return False
            
            # 4. tool_map의 모든 값이 호출 가능한지 확인
            for name, func in tool_map.items():
                if not callable(func):
                    print(f"Error: Function '{name}' in tool_map is not callable")
                    return False
                    
            # 간단한 스키마 JSON 유효성 검증
            for schema in schemas:
                # 함수 객체를 제외한 나머지 부분만 JSON 유효성 검증
                schema_copy = schema.copy()
                
                # 기존 형식의 경우 "function" 키에 있는 함수 객체 제거
                if "function" in schema_copy and callable(schema_copy["function"]):
                    schema_copy = {k: v for k, v in schema_copy.items() if k != "function"}
                
                # 문자열로 직렬화 후 다시 파싱하여 유효성 검증
                json.loads(json.dumps(schema_copy))
                
            return True
            
        except Exception as e:
            print(f"Error validating schema: {e}")
            return False

def validate_tool_module(module) -> bool:
    """
    주어진 모듈이 필요한 도구 인터페이스 요소를 모두 가지고 있는지 확인합니다.
    
    Args:
        module: 검사할 Python 모듈
        
    Returns:
        bool: 유효성 검증 결과 (True: 유효, False: 유효하지 않음)
    """
    # 필수 상수 확인
    if not hasattr(module, 'TOOL_SCHEMAS'):
        print(f"Module {module.__name__} is missing TOOL_SCHEMAS")
        return False
        
    if not hasattr(module, 'TOOL_MAP'):
        print(f"Module {module.__name__} is missing TOOL_MAP")
        return False
    
    # 데이터 타입 확인
    if not isinstance(module.TOOL_SCHEMAS, list):
        print(f"Module {module.__name__} has TOOL_SCHEMAS that is not a list")
        return False
        
    if not isinstance(module.TOOL_MAP, dict):
        print(f"Module {module.__name__} has TOOL_MAP that is not a dict")
        return False
    
    # 스키마 유효성 검증
    return ToolInterface.validate_schema(module.TOOL_SCHEMAS, module.TOOL_MAP)
