# tools/email_tool/utils.py
"""
이메일 도구에서 사용하는 유틸리티 함수들을 제공하는 모듈입니다.
"""

import email
from email.header import decode_header
from typing import Optional
import logging

# --- 로거 설정 ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def clean_header(header: Optional[str]) -> str:
    """
    이메일 헤더를 읽기 쉬운 문자열로 디코딩합니다.
    
    Args:
        header (Optional[str]): 디코딩할 이메일 헤더
        
    Returns:
        str: 디코딩된 헤더 문자열
    """
    if not header:
        return ""
    decoded_parts = decode_header(header)
    parts = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            try:
                parts.append(part.decode(charset or 'utf-8', errors='ignore'))
            except (LookupError, TypeError):
                parts.append(part.decode('utf-8', errors='ignore'))
        else:
            parts.append(str(part))
    return "".join(parts)

def get_email_body(msg: email.message.Message) -> str:
    """
    이메일 메시지에서 텍스트 본문을 추출합니다.
    
    Args:
        msg (email.message.Message): 이메일 메시지 객체
        
    Returns:
        str: 추출된 이메일 본문 텍스트
    """
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == 'text/plain' and 'attachment' not in content_disposition:
                try:
                    return part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                except Exception:
                    continue
    else:
        try:
            return msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='ignore')
        except Exception:
            return "[Could not decode body]"
    return ""