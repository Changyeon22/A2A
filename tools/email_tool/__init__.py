"""이메일 도구 모듈

이 모듈은 Gmail API를 통해 이메일을 검색, 조회, 응답하는 기능을 제공합니다.
"""

from .core import (
    search_emails,
    get_email_details,
    send_reply,
    save_attachments,
    get_daily_email_summary,
    send_email,
    TOOL_SCHEMAS,
    TOOL_MAP,
    validate_tool_interface
)

__all__ = [
    'search_emails',
    'get_email_details',
    'send_reply',
    'save_attachments',
    'get_daily_email_summary',
    'send_email',
    'TOOL_SCHEMAS',
    'TOOL_MAP',
    'validate_tool_interface'
]