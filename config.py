#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
프로젝트 전체 설정 관리 모듈

환경 변수, 기본 설정, 상수 등을 중앙에서 관리합니다.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Config:
    """프로젝트 설정 클래스"""
    
    # API 키 설정
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    NOTION_API_KEY: Optional[str] = os.getenv("NOTION_API_KEY")
    NOTION_PARENT_PAGE_ID: Optional[str] = os.getenv("NOTION_PARENT_PAGE_ID")
    
    # 이메일 설정
    GMAIL_ADDRESS: Optional[str] = os.getenv("GMAIL_ADDRESS")
    GMAIL_APP_PASSWORD: Optional[str] = os.getenv("GMAIL_APP_PASSWORD")
    
    # 로깅 설정
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    
    # 애플리케이션 설정
    APP_NAME: str = "My AI Agent"
    APP_VERSION: str = "1.0.0"
    
    # 모델 설정
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gpt-4o")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "2000"))
    
    # 파일 업로드 설정
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
    ALLOWED_EXTENSIONS: list = [".txt", ".pdf", ".docx", ".md"]
    
    @classmethod
    def validate_required_keys(cls) -> bool:
        """필수 환경 변수가 설정되어 있는지 확인"""
        required_keys = [
            "OPENAI_API_KEY",
        ]
        
        missing_keys = []
        for key in required_keys:
            if not getattr(cls, key):
                missing_keys.append(key)
        
        if missing_keys:
            raise ValueError(f"다음 환경 변수가 설정되지 않았습니다: {', '.join(missing_keys)}")
        
        return True
    
    @classmethod
    def get_database_url(cls) -> str:
        """데이터베이스 URL 생성 (향후 확장용)"""
        return os.getenv("DATABASE_URL", "sqlite:///my_ai_agent.db")
    
    @classmethod
    def is_development(cls) -> bool:
        """개발 환경 여부 확인"""
        return os.getenv("ENVIRONMENT", "development").lower() == "development"
    
    @classmethod
    def is_production(cls) -> bool:
        """프로덕션 환경 여부 확인"""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"

# 전역 설정 인스턴스
config = Config()
