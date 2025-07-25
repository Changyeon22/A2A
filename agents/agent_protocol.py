import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from enum import Enum
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AgentProtocol")

class MessageType(Enum):
    """메시지 유형 열거형"""
    TASK_REQUEST = "task_request"  # 작업 요청
    TASK_RESPONSE = "task_response"  # 작업 응답
    QUERY = "query"  # 정보 조회 
    INFO = "info"  # 정보 제공
    STATUS_UPDATE = "status_update"  # 상태 업데이트
    ERROR = "error"  # 오류 보고
    SYSTEM = "system"  # 시스템 메시지
    FEEDBACK = "feedback"  # 피드백
    CLARIFICATION = "clarification"  # 명확화 요청
    COMPLETION = "completion"  # 완료 알림

class TaskPriority(Enum):
    """작업 우선순위 열거형"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AgentMessage:
    """에이전트 간 통신을 위한 메시지 클래스"""
    
    def __init__(self, 
                 sender_id: str = None,
                 receiver_id: str = None,
                 message_type: Union[MessageType, str] = None,
                 content: Any = None,
                 message_id: str = None,
                 conversation_id: str = None,
                 in_reply_to: str = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 priority: Union[TaskPriority, str] = TaskPriority.MEDIUM,
                 # 호환성을 위한 별칭 파라미터
                 sender: str = None,
                 recipient: str = None,
                 msg_type: str = None,
                 id: str = None,
                 **kwargs):
        """
        메시지 초기화
        
        Args:
            sender_id: 발신자 에이전트 ID (별칭: sender)
            receiver_id: 수신자 에이전트 ID (별칭: recipient)
            message_type: 메시지 유형 (별칭: msg_type)
            content: 메시지 내용
            message_id: 메시지 고유 ID (없을 경우 자동 생성) (별칭: id)
            conversation_id: 대화 고유 ID (없을 경우 자동 생성)
            in_reply_to: 응답하는 메시지의 ID
            metadata: 추가 메타데이터
            priority: 메시지 우선순위
            **kwargs: 추가 키워드 인자
        """
        # 별칭 파라미터 처리
        self.sender_id = sender_id or sender
        self.receiver_id = receiver_id or recipient
        self.message_type = message_type or msg_type
        
        # message_id 처리 - 입력 message_id 또는 id 사용, 둘 다 없으면 새로 생성
        self.message_id = message_id or id or f"msg_{uuid.uuid4().hex}"
        # 호환성을 위해 id도 동일한 값으로 설정
        self.id = self.message_id
        
        self.conversation_id = conversation_id or f"conv_{uuid.uuid4().hex}"
        
        # MessageType 열거형 또는 문자열 처리
        if isinstance(message_type, MessageType):
            self.message_type = message_type.value
        else:
            self.message_type = message_type
            
        # 우선순위 처리
        if isinstance(priority, TaskPriority):
            self.priority = priority.value
        else:
            self.priority = priority
            
        self.content = content
        self.timestamp = datetime.now().isoformat()
        self.metadata = metadata or {}
        self.in_reply_to = in_reply_to
        
        logger.debug(f"Message created: {self.message_id} ({self.message_type})")
        
    def to_dict(self) -> Dict[str, Any]:
        """메시지를 딕셔너리로 변환"""
        return {
            "message_id": self.message_id,
            "conversation_id": self.conversation_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "message_type": self.message_type,
            "content": self.content,
            "timestamp": self.timestamp,
            "in_reply_to": self.in_reply_to,
            "priority": self.priority,
            "metadata": self.metadata
        }
        
    def to_json(self) -> str:
        """메시지를 JSON 문자열로 변환"""
        return json.dumps(self.to_dict())
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """딕셔너리에서 메시지 객체 생성"""
        return cls(
            sender_id=data["sender_id"],
            receiver_id=data["receiver_id"],
            message_type=data["message_type"],
            content=data["content"],
            message_id=data.get("message_id"),
            conversation_id=data.get("conversation_id"),
            in_reply_to=data.get("in_reply_to"),
            metadata=data.get("metadata"),
            priority=data.get("priority", TaskPriority.MEDIUM)
        )
        
    @classmethod
    def from_json(cls, json_str: str) -> 'AgentMessage':
        """JSON 문자열에서 메시지 객체 생성"""
        return cls.from_dict(json.loads(json_str))
    
    def create_reply(self, content: Any, message_type: Union[MessageType, str] = None) -> 'AgentMessage':
        """
        이 메시지에 대한 응답 메시지 생성
        
        Args:
            content: 응답 내용
            message_type: 응답 메시지 유형 (지정되지 않으면 자동으로 응답형 선택)
            
        Returns:
            응답 메시지 객체
        """
        # 메시지 유형이 지정되지 않은 경우 자동 선택
        if message_type is None:
            if self.message_type == MessageType.TASK_REQUEST.value:
                message_type = MessageType.TASK_RESPONSE
            elif self.message_type == MessageType.QUERY.value:
                message_type = MessageType.INFO
            elif self.message_type == MessageType.CLARIFICATION.value:
                message_type = MessageType.INFO
            else:
                message_type = MessageType.FEEDBACK
        
        return AgentMessage(
            sender_id=self.receiver_id,  # 수신자가 발신자가 됨
            receiver_id=self.sender_id,  # 발신자가 수신자가 됨
            message_type=message_type,
            content=content,
            conversation_id=self.conversation_id,
            in_reply_to=self.message_id,
            metadata=self.metadata.copy()  # 기존 메타데이터 유지
        )

class ConversationManager:
    """에이전트 간 대화를 관리하는 클래스"""
    
    def __init__(self):
        """대화 관리자 초기화"""
        self.conversations: Dict[str, List[AgentMessage]] = {}
        logger.info("ConversationManager initialized")
        
    def add_message(self, message: AgentMessage) -> None:
        """
        대화에 메시지 추가
        
        Args:
            message: 추가할 메시지
        """
        conv_id = message.conversation_id
        if conv_id not in self.conversations:
            self.conversations[conv_id] = []
        
        self.conversations[conv_id].append(message)
        logger.debug(f"Message added to conversation {conv_id}")
        
    def get_conversation(self, conversation_id: str) -> List[AgentMessage]:
        """
        대화 기록 조회
        
        Args:
            conversation_id: 대화 ID
            
        Returns:
            메시지 목록
        """
        return self.conversations.get(conversation_id, [])
        
    def get_message_by_id(self, message_id: str) -> Optional[AgentMessage]:
        """
        메시지 ID로 메시지 조회
        
        Args:
            message_id: 메시지 ID
            
        Returns:
            메시지 객체 또는 None
        """
        for messages in self.conversations.values():
            for message in messages:
                if message.message_id == message_id:
                    return message
        return None
    
    def get_latest_conversation_summary(self, conversation_id: str, 
                                       limit: int = 5) -> Dict[str, Any]:
        """
        최근 대화 요약 정보 생성
        
        Args:
            conversation_id: 대화 ID
            limit: 포함할 최근 메시지 수
            
        Returns:
            대화 요약 정보
        """
        messages = self.get_conversation(conversation_id)
        if not messages:
            return {
                "conversation_id": conversation_id,
                "message_count": 0,
                "recent_messages": [],
                "participants": set()
            }
            
        recent = messages[-limit:] if len(messages) > limit else messages
        participants = set()
        for msg in messages:
            participants.add(msg.sender_id)
            participants.add(msg.receiver_id)
            
        return {
            "conversation_id": conversation_id,
            "message_count": len(messages),
            "recent_messages": [msg.to_dict() for msg in recent],
            "participants": list(participants),
            "started_at": messages[0].timestamp,
            "last_updated": messages[-1].timestamp
        }
        
    def export_conversation(self, conversation_id: str) -> str:
        """
        대화 내용을 JSON 형식으로 내보내기
        
        Args:
            conversation_id: 대화 ID
            
        Returns:
            JSON 형식의 대화 내용
        """
        messages = self.get_conversation(conversation_id)
        export_data = {
            "conversation_id": conversation_id,
            "message_count": len(messages),
            "messages": [msg.to_dict() for msg in messages],
            "exported_at": datetime.now().isoformat()
        }
        return json.dumps(export_data, indent=2)
        
    def clear_conversation(self, conversation_id: str) -> bool:
        """
        대화 기록 삭제
        
        Args:
            conversation_id: 대화 ID
            
        Returns:
            성공 여부
        """
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            logger.info(f"Conversation {conversation_id} cleared")
            return True
        return False
