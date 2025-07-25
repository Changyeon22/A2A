#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
planning_tool 모듈

기획서 작성, 다중 페르소나 협업, 문서 요약 및 확장 기능을 제공하는 도구 모듈입니다.

주요 기능:
- 신규 기획서 자동 생성
- 다중 페르소나 기반 협업 계획 수립
- Notion 문서 요약 및 확장
- 다양한 문서 템플릿 지원
"""

from .core import (
    execute_create_new_planning_document,
    execute_collaboration_planning,
    execute_summarize_notion_document,
    execute_expand_notion_document,
    validate_tool_interface
)

from .configs import (
    personas,
    DOCUMENT_TEMPLATES
)

__version__ = "1.0.0"
__author__ = "AI Agent System"

# 모듈에서 외부로 노출할 함수들
__all__ = [
    "execute_create_new_planning_document",
    "execute_collaboration_planning", 
    "execute_summarize_notion_document",
    "execute_expand_notion_document",
    "validate_tool_interface",
    "personas",
    "DOCUMENT_TEMPLATES"
]