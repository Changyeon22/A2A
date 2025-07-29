#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
My AI Agent - 멀티 에이전트 AI 시스템

음성 인식, 이메일 처리, 기획서 작성 등 다양한 AI 기능을 제공하는 
통합 에이전트 시스템의 메인 Streamlit 애플리케이션입니다.
"""

from typing import Dict, Any, Optional, List
from .main import main
from .session_manager import SessionManager
from .ui_manager import UIManager
from .voice_manager import VoiceManager
from .service_manager import ServiceManager

__version__ = "1.0.0"
__author__ = "My AI Agent Team"

__all__ = [
    "main",
    "SessionManager", 
    "UIManager",
    "VoiceManager",
    "ServiceManager"
] 