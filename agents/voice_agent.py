"""
voice_agent.py - A2A 시스템의 음성 처리 에이전트

이 모듈은 음성 변환 작업을 처리하는 VoiceAgent를 정의합니다.
텍스트-음성 변환(TTS) 및 음성-텍스트 변환(STT) 기능을 제공합니다.
"""

import sys
import os
import logging
import importlib
import time
from typing import Dict, Any, List, Optional

# 상위 디렉토리 import를 위한 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from agents.agent_base import BaseAgent
from agents.agent_protocol import AgentMessage, MessageType
from agents.error_handler import ErrorHandler, NetworkError, APIError, APIRateLimitError, ValidationError

# 로거 설정
logger = logging.getLogger(__name__)

class VoiceAgent(BaseAgent):
    """
    음성 처리 에이전트 클래스
    
    음성 변환 도구를 활용하여 음성-텍스트 및 텍스트-음성 변환 작업을 수행합니다.
    """
    
    def __init__(self, agent_id: str = None, name: str = "VoiceSpecialist",
                 specialization: str = "voice_processing", 
                 tools: List[str] = None):
        """
        음성 처리 에이전트 초기화
        
        Args:
            agent_id: 에이전트 ID (없으면 자동 생성)
            name: 에이전트 이름
            specialization: 전문 영역
            tools: 사용할 도구 목록
        """
        # 기본 에이전트 초기화
        super().__init__(agent_id=agent_id, name=name, specialization=specialization)
        
        # 도구 로드
        self.loaded_tools = {}
        
        # 기본 도구 목록
        if tools is None:
            # 기본적으로 voice_tool 도구를 로드
            tools = ["voice_tool"]
        
        self.load_tools(tools)
        
        # 메시지 핸들러 등록
        self.register_callback(MessageType.TASK_REQUEST.value, self._handle_task_request)
        self.register_callback(MessageType.QUERY.value, self._handle_query)
    
    def load_tools(self, tool_names: List[str]) -> None:
        """
        지정된 도구를 로드합니다.
        
        Args:
            tool_names: 로드할 도구 이름 목록
        """
        for tool_name in tool_names:
            try:
                # 동적으로 도구 모듈 import
                module_path = f"tools.{tool_name}.core"
                module = __import__(module_path, fromlist=["TOOL_MAP", "TOOL_SCHEMAS"])
                
                # 도구 함수와 스키마 가져오기
                tool_map = getattr(module, "TOOL_MAP", {})
                tool_schemas = getattr(module, "TOOL_SCHEMAS", [])
                
                # 도구 정보 저장
                self.loaded_tools[tool_name] = {
                    "functions": tool_map,
                    "schemas": tool_schemas
                }
                
                logger.info(f"도구 '{tool_name}' 로드 완료: {len(tool_map)}개 함수")
            except (ImportError, AttributeError) as e:
                logger.error(f"도구 '{tool_name}' 로드 실패: {str(e)}")
    
    def _handle_task_request(self, message: AgentMessage) -> Dict[str, Any]:
        """
        작업 요청 메시지 처리
        
        Args:
            message: 처리할 메시지
            
        Returns:
            처리 결과
        """
        try:
            task_data = message.content.get("task_data", {})
            task_type = task_data.get("type", "")
            
            # 작업 유형 검증
            if not task_type:
                raise ValidationError("작업 유형이 지정되지 않았습니다.", field="type")
                
            logger.info(f"음성 작업 처리 시작: {task_type}")
            
            # 텍스트를 음성으로 변환 (TTS)
            if task_type == "text_to_speech":
                text = task_data.get("text", "")
                detailed_text = task_data.get("detailed_text", "")
                speed = task_data.get("speed", 1.0)
                
                # 텍스트 검증
                if not text and not detailed_text:
                    raise ValidationError("변환할 텍스트가 제공되지 않았습니다.", field="text")
                
                # TTS 기능 확인
                if "voice_tool" not in self.loaded_tools or "speak_text" not in self.loaded_tools["voice_tool"]["functions"]:
                    raise APIError("TTS 기능을 사용할 수 없습니다.", api_name="voice_tool")
                
                try:
                    # 지수 백오프를 사용한 재시도 로직 적용
                    def tts_with_retry():
                        speak_text_fn = self.loaded_tools["voice_tool"]["functions"]["speak_text"]
                        result = speak_text_fn(text=text, detailed_text=detailed_text, speed=speed)
                        if not result:
                            raise APIError("음성 생성에 실패했습니다.", api_name="speak_text")
                        return result
                    
                    audio_bytes = ErrorHandler.retry_with_backoff(
                        tts_with_retry,
                        max_retries=3,
                        exceptions=(NetworkError, APIError)
                    )
                    
                    response_data = {
                        "status": "success",
                        "audio_data": audio_bytes,
                        "original_text": text,
                        "detailed_text": detailed_text
                    }
                    
                except (NetworkError, APIError) as e:
                    logger.warning(f"TTS 변환 중 오류 발생: {str(e)}")
                    raise
                    
            # 음성을 텍스트로 변환 (STT)
            elif task_type == "speech_to_text":
                audio_data = task_data.get("audio_data")
                
                # 오디오 데이터 검증
                if not audio_data:
                    raise ValidationError("변환할 오디오 데이터가 제공되지 않았습니다.", field="audio_data")
                
                # STT 기능 확인
                stt_function_name = "speech_to_text_from_mic_data"
                if ("voice_tool" not in self.loaded_tools or 
                    stt_function_name not in self.loaded_tools["voice_tool"]["functions"]):
                    raise APIError("STT 기능을 사용할 수 없습니다.", api_name="voice_tool")
                
                try:
                    # 지수 백오프를 사용한 재시도 로직 적용
                    def stt_with_retry():
                        stt_fn = self.loaded_tools["voice_tool"]["functions"][stt_function_name]
                        result = stt_fn(audio_data)
                        if not result:
                            raise APIError("음성 인식에 실패했습니다.", api_name="speech_to_text")
                        return result
                    
                    result = ErrorHandler.retry_with_backoff(
                        stt_with_retry,
                        max_retries=3,
                        exceptions=(NetworkError, APIError)
                    )
                    
                    response_data = result
                    
                except (NetworkError, APIError) as e:
                    logger.warning(f"STT 변환 중 오류 발생: {str(e)}")
                    raise
                    
            else:
                raise ValidationError(f"지원하지 않는 작업 유형입니다: {task_type}", field="type")
                
            # 응답 반환
            return {
                "status": "success",
                "task_id": message.content.get("task_id"),
                "result": response_data
            }
            
        except ValidationError as e:
            # 검증 오류 처리
            logger.warning(f"검증 오류: {str(e)}")
            context = {
                "agent_id": self.agent_id,
                "message_id": message.id,
                "task_type": message.content.get("task_data", {}).get("type", "")
            }
            return ErrorHandler.handle_error(e, context)
            
        except NetworkError as e:
            # 네트워크 오류 처리
            logger.warning(f"네트워크 오류: {str(e)}")
            context = {
                "agent_id": self.agent_id,
                "message_id": message.id
            }
            return ErrorHandler.handle_error(e, context)
            
        except APIError as e:
            # API 오류 처리
            logger.warning(f"API 오류: {str(e)}")
            context = {
                "agent_id": self.agent_id,
                "message_id": message.id,
                "api": getattr(e, "details", {}).get("api_name", "unknown")
            }
            return ErrorHandler.handle_error(e, context)
            
        except Exception as e:
            # 기타 예외 처리
            logger.error(f"예상치 못한 오류 발생: {str(e)}", exc_info=True)
            context = {
                "agent_id": self.agent_id,
                "message_id": message.id
            }
            return ErrorHandler.handle_error(e, context)
    
    def _handle_query(self, message: AgentMessage) -> Dict[str, Any]:
        """
        쿼리 메시지를 처리합니다.
        
        Args:
            message: 처리할 메시지 객체
            
        Returns:
            처리 결과
        """
        try:
            query = message.content.get("query", "")
            
            # 쿼리 검증
            if not query:
                raise ValidationError("쿼리가 제공되지 않았습니다.", field="query")
            
            # 쿼리 유형에 따라 처리
            if "tools" in query.lower() or "capabilities" in query.lower():
                # 지원하는 도구 및 기능 목록 반환
                available_tools = {}
                for tool_name, tool_data in self.loaded_tools.items():
                    available_tools[tool_name] = list(tool_data["functions"].keys())
                
                response_data = {
                    "status": "success",
                    "tools": available_tools
                }
            else:
                # 기본 에이전트 정보 반환
                response_data = {
                    "status": "success",
                    "agent_info": {
                        "name": self.name,
                        "id": self.id,
                        "specialization": self.specialization,
                        "capabilities": [
                            "텍스트-음성 변환 (TTS)",
                            "음성-텍스트 변환 (STT)"
                        ]
                    }
                }
            
            # 응답 반환
            return {
                "status": "success",
                "query_id": message.content.get("query_id"),
                "result": response_data
            }
            
        except ValidationError as e:
            # 검증 오류 처리
            logger.warning(f"쿼리 검증 오류: {str(e)}")
            context = {
                "agent_id": self.agent_id,
                "message_id": message.id,
                "query": message.content.get("query", "")
            }
            return ErrorHandler.handle_error(e, context)
            
        except Exception as e:
            # 기타 예외 처리
            logger.error(f"쿼리 처리 중 예상치 못한 오류 발생: {str(e)}", exc_info=True)
            context = {
                "agent_id": self.agent_id,
                "message_id": message.id,
                "query": message.content.get("query", "")
            }
            return ErrorHandler.handle_error(e, context)
            
    def _text_to_speech(self, text: str, detailed_text: str = "", speed: float = 1.0) -> bytes:
        """
        텍스트를 음성으로 변환
        
        Args:
            text: 변환할 텍스트
            detailed_text: 상세 텍스트 (있을 경우)
            speed: 재생 속도
            
        Returns:
            음성 데이터 (bytes)
        """
        if "voice_tool" not in self.loaded_tools or "speak_text" not in self.loaded_tools["voice_tool"]["functions"]:
            raise APIError("TTS 기능을 사용할 수 없습니다.", api_name="voice_tool")
        
        speak_text_fn = self.loaded_tools["voice_tool"]["functions"]["speak_text"]
        result = speak_text_fn(text=text, detailed_text=detailed_text, speed=speed)
        
        if not result:
            raise APIError("음성 생성에 실패했습니다.", api_name="speak_text")
            
        return result
        
    def _speech_to_text(self, audio_data: bytes) -> Dict[str, Any]:
        """
        음성을 텍스트로 변환
        
        Args:
            audio_data: 변환할 음성 데이터
            
        Returns:
            변환 결과 (텍스트 및 추가 정보)
        """
        stt_function_name = "speech_to_text_from_mic_data"
        
        if ("voice_tool" not in self.loaded_tools or 
            stt_function_name not in self.loaded_tools["voice_tool"]["functions"]):
            raise APIError("STT 기능을 사용할 수 없습니다.", api_name="voice_tool")
            
        stt_fn = self.loaded_tools["voice_tool"]["functions"][stt_function_name]
        result = stt_fn(audio_data)
        
        if not result:
            raise APIError("음성 인식에 실패했습니다.", api_name="speech_to_text")
            
        return result
