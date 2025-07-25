import importlib
import logging
import uuid
from typing import Dict, List, Any, Optional, Type, Callable
from datetime import datetime

from .agent_base import BaseAgent
from .agent_protocol import AgentMessage, MessageType, ConversationManager

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AgentManager")

class AgentManager:
    """
    에이전트 관리자 클래스
    
    여러 에이전트를 생성, 관리하고 에이전트 간 통신을 중개
    """
    
    def __init__(self):
        """에이전트 관리자 초기화"""
        self.agents: Dict[str, BaseAgent] = {}  # 에이전트 ID와 인스턴스 매핑
        self.agent_types: Dict[str, Type[BaseAgent]] = {}  # 에이전트 유형 등록
        self.active_workflows: Dict[str, Dict[str, Any]] = {}  # 활성 워크플로우 추적
        self.conversation_manager = ConversationManager()  # 대화 관리자
        self.event_callbacks: Dict[str, List[Callable]] = {}  # 이벤트 콜백 등록
        
        logger.info("AgentManager initialized")
        
    def register_agent_type(self, name: str, agent_class: Type[BaseAgent]) -> bool:
        """
        에이전트 타입 등록
        
        Args:
            name: 에이전트 타입 이름
            agent_class: 에이전트 클래스
            
        Returns:
            성공 여부
        """
        if name in self.agent_types:
            logger.warning(f"Agent type {name} already registered")
            return False
            
        self.agent_types[name] = agent_class
        logger.info(f"Agent type '{name}' registered")
        return True
        
    def create_agent(self, agent_type: str, name: Optional[str] = None, 
                    agent_id: Optional[str] = None, specialization: Optional[str] = None,
                    tools: Optional[List[str]] = None) -> Optional[BaseAgent]:
        """
        특정 타입의 에이전트 생성
        
        Args:
            agent_type: 에이전트 타입 이름 (등록된 타입 중에서)
            name: 에이전트 이름
            agent_id: 고유 ID (없으면 자동 생성)
            specialization: 특화 영역
            tools: 사용 가능한 도구 목록
            
        Returns:
            생성된 에이전트 객체 또는 None
        """
        # 에이전트 ID 생성
        agent_id = agent_id or f"{agent_type}_{uuid.uuid4().hex[:8]}"
        
        # 이미 존재하는 ID면 거부
        if agent_id in self.agents:
            logger.error(f"Agent ID {agent_id} already exists")
            return None
            
        # 에이전트 타입 검증
        if agent_type not in self.agent_types:
            logger.error(f"Unknown agent type: {agent_type}")
            return None
            
        # 에이전트 생성
        try:
            agent_class = self.agent_types[agent_type]
            agent = agent_class(
                agent_id=agent_id,
                name=name or agent_type.capitalize(),
                specialization=specialization or "general",
                tools=tools or []
            )
            
            # 관리자에 등록
            self.agents[agent_id] = agent
            logger.info(f"Agent created: {agent.name} (ID: {agent_id}, Type: {agent_type})")
            
            # 생성 이벤트 발행
            self._trigger_event("agent_created", {"agent_id": agent_id, "agent": agent})
            
            return agent
            
        except Exception as e:
            logger.error(f"Error creating agent: {str(e)}")
            return None
            
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        에이전트 ID로 에이전트 조회
        
        Args:
            agent_id: 에이전트 ID
            
        Returns:
            에이전트 객체 또는 None
        """
        return self.agents.get(agent_id)
        
    def list_agents(self) -> List[Dict[str, Any]]:
        """
        모든 에이전트 정보 목록 조회
        
        Returns:
            에이전트 정보 목록
        """
        return [agent.get_agent_info() for agent in self.agents.values()]
        
    def remove_agent(self, agent_id: str) -> bool:
        """
        에이전트 제거
        
        Args:
            agent_id: 제거할 에이전트 ID
            
        Returns:
            성공 여부
        """
        if agent_id not in self.agents:
            logger.warning(f"Agent {agent_id} not found")
            return False
            
        agent = self.agents.pop(agent_id)
        logger.info(f"Agent removed: {agent.name} (ID: {agent_id})")
        
        # 제거 이벤트 발행
        self._trigger_event("agent_removed", {"agent_id": agent_id})
        
        return True
        
    def send_message(self, sender_id: str, receiver_id: str, message_type: str,
                    content: Any, metadata: Optional[Dict[str, Any]] = None) -> Optional[AgentMessage]:
        """
        에이전트 간 메시지 전송
        
        Args:
            sender_id: 발신자 에이전트 ID
            receiver_id: 수신자 에이전트 ID
            message_type: 메시지 유형
            content: 메시지 내용
            metadata: 추가 메타데이터
            
        Returns:
            전송된 메시지 또는 None
        """
        # 발신자 검증
        if sender_id not in self.agents:
            logger.error(f"Unknown sender agent: {sender_id}")
            return None
            
        # 수신자 검증
        if receiver_id not in self.agents:
            logger.error(f"Unknown receiver agent: {receiver_id}")
            return None
            
        # 메시지 생성
        message = AgentMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=message_type,
            content=content,
            metadata=metadata
        )
        
        # 대화 기록 추가
        self.conversation_manager.add_message(message)
        
        # 수신자에게 메시지 전달
        receiver = self.agents[receiver_id]
        response = receiver.receive_message(message.to_dict())
        
        # 메시지 전송 이벤트 발행
        self._trigger_event("message_sent", {
            "message": message.to_dict(),
            "response": response
        })
        
        logger.info(f"Message delivered: {sender_id} -> {receiver_id} ({message_type})")
        return message
    
    def register_event_callback(self, event_type: str, callback: Callable) -> None:
        """
        이벤트 발생 시 실행할 콜백 함수 등록
        
        Args:
            event_type: 이벤트 유형
            callback: 콜백 함수
        """
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = []
            
        self.event_callbacks[event_type].append(callback)
        logger.info(f"Callback registered for event '{event_type}'")
        
    def _trigger_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        내부적으로 이벤트 발생 시 등록된 콜백 실행
        
        Args:
            event_type: 이벤트 유형
            event_data: 이벤트 데이터
        """
        if event_type not in self.event_callbacks:
            return
            
        for callback in self.event_callbacks[event_type]:
            try:
                callback(event_data)
            except Exception as e:
                logger.error(f"Error in event callback: {str(e)}")
                
    def create_workflow(self, workflow_id: Optional[str] = None) -> str:
        """
        새 워크플로우 생성
        
        Args:
            workflow_id: 워크플로우 ID (없으면 자동 생성)
            
        Returns:
            생성된 워크플로우 ID
        """
        workflow_id = workflow_id or f"workflow_{uuid.uuid4().hex[:8]}"
        
        if workflow_id in self.active_workflows:
            logger.warning(f"Workflow ID {workflow_id} already exists")
            return workflow_id
            
        self.active_workflows[workflow_id] = {
            "id": workflow_id,
            "status": "created",
            "created_at": datetime.now().isoformat(),
            "agents": [],
            "tasks": [],
            "results": {}
        }
        
        logger.info(f"Workflow created: {workflow_id}")
        return workflow_id
        
    def add_agent_to_workflow(self, workflow_id: str, agent_id: str, role: str = "participant") -> bool:
        """
        워크플로우에 에이전트 추가
        
        Args:
            workflow_id: 워크플로우 ID
            agent_id: 에이전트 ID
            role: 워크플로우 내 역할
            
        Returns:
            성공 여부
        """
        if workflow_id not in self.active_workflows:
            logger.error(f"Unknown workflow: {workflow_id}")
            return False
            
        if agent_id not in self.agents:
            logger.error(f"Unknown agent: {agent_id}")
            return False
            
        workflow = self.active_workflows[workflow_id]
        
        # 이미 워크플로우에 포함된 에이전트인지 확인
        for agent_info in workflow["agents"]:
            if agent_info["agent_id"] == agent_id:
                logger.warning(f"Agent {agent_id} already in workflow {workflow_id}")
                return True
                
        # 에이전트 추가
        workflow["agents"].append({
            "agent_id": agent_id,
            "role": role,
            "added_at": datetime.now().isoformat()
        })
        
        logger.info(f"Agent {agent_id} added to workflow {workflow_id} as {role}")
        return True
