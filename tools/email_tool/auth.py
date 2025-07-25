# tools/email_tool/auth.py
"""
이메일 도구의 인증 관련 기능을 제공하는 모듈입니다.
"""

import os
import imaplib
import smtplib
import logging
from typing import Tuple, Optional

from .configs import IMAP_SERVER, SMTP_SERVER, SMTP_PORT, ERROR_CREDENTIALS_NOT_CONFIGURED

# --- 로거 설정 ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_credentials() -> Tuple[str, str]:
    """
    환경 변수에서 Gmail 계정 정보를 가져옵니다.
    
    Returns:
        Tuple[str, str]: (Gmail 주소, Gmail 앱 비밀번호) 튜플
        
    Raises:
        ValueError: 필요한 환경 변수가 설정되지 않은 경우
    """
    gmail_address = os.environ.get('GMAIL_ADDRESS')
    gmail_app_password = os.environ.get('GMAIL_APP_PASSWORD')
    
    if not gmail_address or not gmail_app_password:
        logger.error("Gmail credentials not configured in environment variables")
        raise ValueError(ERROR_CREDENTIALS_NOT_CONFIGURED)
        
    return gmail_address, gmail_app_password

def get_imap_connection() -> imaplib.IMAP4_SSL:
    """
    IMAP 서버에 연결하고 로그인합니다.
    
    Returns:
        imaplib.IMAP4_SSL: 인증된 IMAP 연결 객체
        
    Raises:
        ValueError: 인증 정보가 없거나 연결에 실패한 경우
    """
    try:
        gmail_address, gmail_app_password = get_credentials()
        
        # IMAP 서버에 연결
        imap = imaplib.IMAP4_SSL(IMAP_SERVER)
        
        # 로그인
        imap.login(gmail_address, gmail_app_password)
        
        return imap
    except Exception as e:
        logger.error(f"IMAP connection error: {str(e)}")
        raise

def get_smtp_connection() -> smtplib.SMTP:
    """
    SMTP 서버에 연결하고 로그인합니다.
    
    Returns:
        smtplib.SMTP: 인증된 SMTP 연결 객체
        
    Raises:
        ValueError: 인증 정보가 없거나 연결에 실패한 경우
    """
    try:
        gmail_address, gmail_app_password = get_credentials()
        
        # SMTP 서버에 연결
        smtp = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        
        # 로그인
        smtp.login(gmail_address, gmail_app_password)
        
        return smtp
    except Exception as e:
        logger.error(f"SMTP connection error: {str(e)}")
        raise