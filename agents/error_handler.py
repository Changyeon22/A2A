"""
에이전트 시스템 오류 처리 모듈

이 모듈은 A2A 시스템에서 발생할 수 있는 다양한 오류를 처리하고 관리합니다.
"""

import logging
from typing import Dict, Any, Optional
import traceback
import time
from enum import Enum

logger = logging.getLogger("ErrorHandler")


class ErrorSeverity(Enum):
    """오류 심각도 수준"""
    LOW = 1  # 낮은 심각도, 계속 진행 가능
    MEDIUM = 2  # 중간 심각도, 재시도 가능
    HIGH = 3  # 높은 심각도, 작업 중단 필요
    CRITICAL = 4  # 치명적인 심각도, 시스템 종료 필요


class AgentError(Exception):
    """에이전트 시스템 기본 오류 클래스"""
    
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 error_code: str = "AGENT_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = time.time()
        
    def to_dict(self) -> Dict[str, Any]:
        """오류 정보를 딕셔너리로 변환"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "severity": self.severity.name,
            "details": self.details,
            "timestamp": self.timestamp
        }


class NetworkError(AgentError):
    """네트워크 관련 오류"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            error_code="NETWORK_ERROR",
            details=details
        )


class APIError(AgentError):
    """API 호출 관련 오류"""
    
    def __init__(self, message: str, api_name: str, status_code: Optional[int] = None,
                details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({"api_name": api_name, "status_code": status_code})
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            error_code="API_ERROR",
            details=details
        )


class APIRateLimitError(APIError):
    """API 속도 제한 오류"""
    
    def __init__(self, message: str, api_name: str, retry_after: Optional[int] = None):
        super().__init__(
            message,
            api_name=api_name,
            details={"retry_after": retry_after}
        )
        self.error_code = "API_RATE_LIMIT"
        self.retry_after = retry_after


class ConfigurationError(AgentError):
    """구성 관련 오류"""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            error_code="CONFIG_ERROR",
            details={"config_key": config_key} if config_key else {}
        )


class ValidationError(AgentError):
    """입력 데이터 검증 오류"""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        details = {}
        if field:
            details["field"] = field
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            error_code="VALIDATION_ERROR",
            details=details
        )


class ErrorHandler:
    """오류 처리 및 관리 클래스"""
    
    @staticmethod
    def handle_error(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        발생한 오류를 처리하고 적절한 응답 생성
        
        Args:
            error: 발생한 예외
            context: 오류 컨텍스트 정보
            
        Returns:
            오류 처리 결과 딕셔너리
        """
        context = context or {}
        
        # 표준화된 오류 정보
        error_info = {
            "success": False,
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context
        }
        
        # 스택 트레이스 (개발 모드에서만 포함)
        if logger.level <= logging.DEBUG:
            error_info["stack_trace"] = traceback.format_exc()
            
        # AgentError 타입은 추가 정보 포함
        if isinstance(error, AgentError):
            error_info.update({
                "error_code": error.error_code,
                "severity": error.severity.name,
                "details": error.details
            })
            
            # 심각도에 따라 로깅 수준 결정
            if error.severity == ErrorSeverity.CRITICAL:
                logger.critical(f"Critical Error: {error}", exc_info=True)
            elif error.severity == ErrorSeverity.HIGH:
                logger.error(f"High Severity Error: {error}", exc_info=True)
            elif error.severity == ErrorSeverity.MEDIUM:
                logger.warning(f"Medium Severity Error: {error}")
            else:
                logger.info(f"Low Severity Error: {error}")
                
            # API 속도 제한 오류의 경우 재시도 정보 제공
            if isinstance(error, APIRateLimitError) and error.retry_after:
                error_info["retry_after"] = error.retry_after
        else:
            # 기본 예외의 경우 ERROR 레벨로 로깅
            logger.error(f"Unhandled Error: {error}", exc_info=True)
            
        return {
            "status": "error",
            "error_info": error_info,
            "result": {"error": str(error)}  # 테스트 호환성을 위한 result 키
        }
    
    @staticmethod
    def retry_with_backoff(func, max_retries=3, initial_delay=1, backoff_factor=2, 
                          exceptions=(NetworkError, APIRateLimitError)):
        """
        오류 발생 시 지수 백오프로 재시도하는 함수
        
        Args:
            func: 재시도할 함수
            max_retries: 최대 재시도 횟수
            initial_delay: 초기 대기 시간(초)
            backoff_factor: 백오프 계수
            exceptions: 재시도할 예외 클래스 튜플
            
        Returns:
            원래 함수의 반환값
        """
        retries = 0
        delay = initial_delay
        
        while True:
            try:
                return func()
            except exceptions as e:
                retries += 1
                
                # 재시도 횟수 초과 시 예외 다시 발생
                if retries >= max_retries:
                    logger.warning(f"Max retries ({max_retries}) exceeded. Last error: {e}")
                    raise
                
                # API 속도 제한의 경우 제공된 재시도 시간 사용
                if isinstance(e, APIRateLimitError) and e.retry_after:
                    delay = e.retry_after
                
                # 로그 출력 및 대기
                logger.info(f"Retry {retries}/{max_retries} after {delay} seconds. Error: {e}")
                time.sleep(delay)
                
                # 다음 대기 시간 계산
                delay *= backoff_factor
