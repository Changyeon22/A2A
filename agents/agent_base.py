import uuid
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AgentBase")

class BaseAgent:
    """
    모든 에이전트의 기본 클래스.
    각 에이전트는 고유 ID, 특화 영역, 도구 모음을 가지며 다른 에이전트와 통신 가능.
    """
    
    def __init__(self, agent_id: str = None, name: str = "BaseAgent", 
                 specialization: str = "general", tools: List[str] = None):
        """
        에이전트 초기화
        
        Args:
            agent_id: 에이전트 고유 ID (없으면 자동 생성)
            name: 에이전트 이름
            specialization: 에이전트 특화 영역
            tools: 에이전트가 사용 가능한 도구 목록
        """
        self.agent_id = agent_id or f"agent_{uuid.uuid4().hex[:8]}"
        self.name = name
        self.specialization = specialization
        self.tools = tools or []
        self.memory = {}  # 에이전트 작업 기억 저장
        self.conversation_history = []  # 대화 기록
        self.callbacks = {}  # 이벤트 발생 시 실행할 콜백 함수
        self.created_at = datetime.now()
        logger.info(f"Agent initialized: {self.name} ({self.agent_id}), specialization: {self.specialization}")
    
    def process_task(self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        작업 처리 기본 메서드 (구체적인 에이전트에서 오버라이드해야 함)
        
        Args:
            task_data: 처리할 작업 데이터
            context: 작업 컨텍스트 정보
            
        Returns:
            처리 결과
        """
        logger.warning(f"Agent {self.name} using default process_task implementation - should be overridden")
        return {
            "status": "not_implemented",
            "message": "This method should be implemented by specific agent classes",
            "agent_id": self.agent_id
        }
    
    def communicate(self, target_agent_id: str, message_type: str, content: Any, 
                   metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        다른 에이전트에게 메시지 전송 (실제 구현은 메시지 브로커가 담당)
        
        Args:
            target_agent_id: 대상 에이전트 ID
            message_type: 메시지 유형 (request, response, notification 등)
            content: 메시지 내용
            metadata: 추가 메타데이터
            
        Returns:
            전송 결과
        """
        # 메시지 객체 생성 (실제로는 agent_manager를 통해 전달됨)
        message = {
            "sender_id": self.agent_id,
            "receiver_id": target_agent_id,
            "message_type": message_type,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Agent {self.name} sending message to {target_agent_id}: {message_type}")
        # 실제 전송은 AgentManager에서 처리 (여기서는 로깅만)
        self.conversation_history.append(message)
        return {
            "status": "message_created",
            "message": message
        }
    
    def receive_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        다른 에이전트로부터 메시지 수신 처리
        
        Args:
            message: 수신된 메시지
            
        Returns:
            처리 결과
        """
        sender_id = message.get("sender_id", "unknown")
        message_type = message.get("message_type", "unknown")
        
        logger.info(f"Agent {self.name} received message from {sender_id}: {message_type}")
        self.conversation_history.append(message)
        
        # 메시지 타입에 따른 콜백 함수가 등록되어 있으면 실행
        if message_type in self.callbacks:
            return self.callbacks[message_type](message)
        
        # 기본 응답
        return {
            "status": "received",
            "message": "Message received but no specific handler registered",
            "agent_id": self.agent_id
        }
    
    def add_tool(self, tool_name: str) -> bool:
        """
        에이전트에 새 도구 추가
        
        Args:
            tool_name: 추가할 도구 이름
            
        Returns:
            성공 여부
        """
        if tool_name not in self.tools:
            self.tools.append(tool_name)
            logger.info(f"Tool '{tool_name}' added to agent {self.name}")
            return True
        return False
    
    def register_callback(self, event_type: str, callback: Callable) -> None:
        """
        특정 이벤트 발생 시 실행할 콜백 함수 등록
        
        Args:
            event_type: 이벤트 유형
            callback: 콜백 함수
        """
        self.callbacks[event_type] = callback
        logger.info(f"Callback registered for event '{event_type}' in agent {self.name}")
    
    def update_memory(self, key: str, value: Any) -> None:
        """
        에이전트 메모리에 정보 저장
        
        Args:
            key: 저장할 정보의 키
            value: 저장할 값
        """
        self.memory[key] = value
    
    def get_memory(self, key: str, default: Any = None) -> Any:
        """
        에이전트 메모리에서 정보 조회
        
        Args:
            key: 조회할 정보의 키
            default: 키가 없을 경우 반환할 기본값
            
        Returns:
            저장된 값 또는 기본값
        """
        return self.memory.get(key, default)
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        에이전트 정보 조회
        
        Returns:
            에이전트 정보
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "specialization": self.specialization,
            "tools": self.tools,
            "created_at": self.created_at.isoformat(),
            "conversation_count": len(self.conversation_history)
        }

    def __str__(self) -> str:
        """문자열 표현"""
        return f"{self.name} (ID: {self.agent_id}, Spec: {self.specialization})"
