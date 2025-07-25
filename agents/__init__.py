#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
agents 모듈

멀티 에이전트 시스템의 핵심 구성 요소들을 제공하는 모듈입니다.

주요 기능:
- 에이전트 기본 클래스 및 프로토콜 정의
- 에이전트 간 메시지 통신 시스템
- 에이전트 생명주기 관리
- 대화 및 작업 우선순위 관리
"""

from .agent_base import BaseAgent
from .agent_protocol import AgentMessage, MessageType, TaskPriority, ConversationManager
from .agent_manager import AgentManager

# 구체적인 에이전트 구현체들
from .voice_agent import VoiceAgent
from .email_agent import EmailAgent

__version__ = "1.0.0"
__author__ = "AI Agent System"

# 모듈에서 외부로 노출할 클래스들
__all__ = [
    'BaseAgent',
    'AgentMessage',
    'MessageType',
    'TaskPriority',
    'ConversationManager',
    'AgentManager',
    'VoiceAgent',
    'EmailAgent'
]
