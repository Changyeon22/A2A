#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
로깅 구성 모듈

프로젝트 전체에서 사용할 표준 로깅 설정을 제공합니다.
"""

import logging
import logging.config
import os
from datetime import datetime

def setup_logging(log_level: str = "INFO", log_dir: str = "logs"):
    """
    프로젝트 전체 로깅 설정
    
    Args:
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: 로그 파일 저장 디렉토리
    """
    # 로그 디렉토리 생성
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 로그 파일명 (날짜별)
    log_filename = os.path.join(log_dir, f'my_ai_agent_{datetime.now().strftime("%Y%m%d")}.log')
    
    # 로깅 설정
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'detailed': {
                'format': '%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d: %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
        },
        'handlers': {
            'console': {
                'level': log_level,
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'detailed',
                'filename': log_filename,
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf-8'
            },
        },
        'loggers': {
            'my_ai_agent': {
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
                'propagate': False
            },
        },
        'root': {
            'level': log_level,
            'handlers': ['console', 'file']
        }
    }
    
    logging.config.dictConfig(logging_config)
    
    # 로깅 시작 메시지
    logger = logging.getLogger('my_ai_agent')
    logger.info(f"로깅 시스템이 초기화되었습니다. 로그 레벨: {log_level}")
    logger.info(f"로그 파일: {log_filename}")

def get_logger(name: str) -> logging.Logger:
    """
    로거 인스턴스를 반환합니다.
    
    Args:
        name: 로거 이름 (일반적으로 모듈명)
        
    Returns:
        로거 인스턴스
    """
    return logging.getLogger(f'my_ai_agent.{name}')
