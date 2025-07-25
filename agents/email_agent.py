"""
email_agent.py - A2A 시스템의 이메일 처리 에이전트

이 모듈은 이메일 작업을 처리하는 EmailAgent를 정의합니다.
이메일 검색, 조회, 응답 및 첨부파일 저장 등의 기능을 제공합니다.
"""

import sys
import os
import logging
from typing import Dict, List, Any, Optional, Union
import openai

# 상위 디렉토리 import를 위한 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from agents.agent_base import BaseAgent
from agents.agent_protocol import AgentMessage, MessageType
from agents.error_handler import ErrorHandler, NetworkError, APIError, APIRateLimitError, ValidationError

# 로거 설정
logger = logging.getLogger(__name__)

class MailSummaryAgent(BaseAgent):
    """
    메일 본문 요약 담당 에이전트
    """
    def process_task(self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # TODO: LLM을 활용한 메일 요약 구현
        email_body = task_data.get("email_body", "")
        return {"status": "success", "summary": f"[요약 결과] {email_body[:50]}... (요약 내용은 추후 구현)"}

class MailAnalysisAgent(BaseAgent):
    """
    메일 핵심 내용 분석/중요도/의사결정 지원 담당 에이전트
    """
    def process_task(self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        email_body = task_data.get("email_body", "")
        email_subject = task_data.get("email_subject", "")
        email_from = task_data.get("email_from", "")
        email_date = task_data.get("email_date", "")
        
        if not email_body and not email_subject:
            return {"status": "error", "error": "분석할 메일 내용이 없습니다."}
        
        try:
            from openai import OpenAI
            import os
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise Exception("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
            client = OpenAI(api_key=api_key)
            
            prompt = f"""
            다음 이메일의 중요도와 의사결정을 분석해주세요.
            
            [제목]: {email_subject}
            [발신자]: {email_from}
            [날짜]: {email_date}
            [본문]: {email_body}
            
            다음 형식으로 JSON 응답해주세요:
            {{
                "summary": "메일 핵심 내용 요약 (50자 이내)",
                "importance": "매우 중요|중요|일반|낮음",
                "action": "즉시 답장 필요|답장 필요|참조만 해도 됨|아카이브",
                "reason": "분석 근거 (간단히)"
            }}
            
            중요도 판단 기준:
            - 매우 중요: 긴급한 업무, 마감일, 중요한 의사결정
            - 중요: 업무 관련, 답장 필요, 후속 조치 필요
            - 일반: 정보 공유, 참고용, 일상적 업무
            - 낮음: 광고, 뉴스레터, 개인적 내용
            
            의사결정 기준:
            - 즉시 답장 필요: 긴급한 질문, 마감일, 중요한 요청
            - 답장 필요: 질문이나 요청이 있음, 업무 관련
            - 참조만 해도 됨: 정보 공유, 참고용
            - 아카이브: 광고, 불필요한 메일
            """
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.3,
            )
            
            analysis_text = response.choices[0].message.content.strip()
            
            # JSON 파싱 시도
            try:
                import json
                analysis_data = json.loads(analysis_text)
                return {
                    "status": "success",
                    "analysis": analysis_data.get("summary", "분석 완료"),
                    "importance": analysis_data.get("importance", "일반"),
                    "action": analysis_data.get("action", "참조만 해도 됨"),
                    "reason": analysis_data.get("reason", "분석 완료")
                }
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 텍스트에서 추출
                return {
                    "status": "success",
                    "analysis": analysis_text[:50] + "..." if len(analysis_text) > 50 else analysis_text,
                    "importance": "일반",
                    "action": "참조만 해도 됨",
                    "reason": "LLM 분석 완료"
                }
                
        except Exception as e:
            logger.error(f"메일 분석 실패: {e}")
            # fallback: 기본 분석
            return {
                "status": "success", 
                "analysis": f"{email_body[:50]}... (분석 실패)",
                "importance": "일반",
                "action": "참조만 해도 됨",
                "reason": f"분석 실패: {str(e)}"
            }

class MailAttachmentAgent(BaseAgent):
    """
    메일 첨부파일 추출/저장 담당 에이전트
    """
    def process_task(self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # TODO: 첨부파일 추출/저장 구현
        attachments = task_data.get("attachments", [])
        return {"status": "success", "saved_files": [f"/local/path/{a['filename']}" for a in attachments]}

class MailContextAgent(BaseAgent):
    """
    메일 대화 히스토리/스레드 분석 담당 에이전트
    """
    def process_task(self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # TODO: 과거 대화/스레드 분석 구현
        history = task_data.get("history", [])
        return {"status": "success", "context": f"[히스토리 분석 결과] {len(history)}개 대화 (분석 내용은 추후 구현)"}

class MailReplyAgent(BaseAgent):
    """
    답장 초안 생성(일관성, 톤 유지) 담당 에이전트
    """
    def process_task(self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # TODO: LLM을 활용한 답장 초안 생성 구현
        email_body = task_data.get("email_body", "")
        context_info = task_data.get("context", "")
        return {"status": "success", "reply": f"[답장 초안] (일관성/톤 유지, 내용은 추후 구현)"}

class EmailAgent(BaseAgent):
    """
    이메일 처리 에이전트 클래스
    
    이메일 도구를 활용하여 이메일 검색, 조회, 응답 및 첨부파일 저장 작업을 수행합니다.
    """
    
    def __init__(self, agent_id: str = None, name: str = "EmailSpecialist",
                 specialization: str = "email_processing", 
                 tools: List[str] = None):
        """
        이메일 처리 에이전트 초기화
        
        Args:
            agent_id: 에이전트 ID (없으면 자동 생성)
            name: 에이전트 이름
            specialization: 전문 영역
            tools: 사용할 도구 목록
        """
        # 기본 에이전트 초기화
        super().__init__(agent_id=agent_id, name=name, specialization=specialization)
        
        # 도구 로드
        self.loaded_tools = {}
        
        # 기본 도구 목록
        if tools is None:
            # 기본적으로 email_tool 도구를 로드
            tools = ["email_tool"]
        
        self.load_tools(tools)
        
        # 메시지 핸들러 등록
        self.register_callback(MessageType.TASK_REQUEST.value, self._handle_task_request)
        self.register_callback(MessageType.QUERY.value, self._handle_query)
    
    def load_tools(self, tool_names: List[str]) -> None:
        """
        지정된 도구를 로드합니다.
        
        Args:
            tool_names: 로드할 도구 이름 목록
        """
        for tool_name in tool_names:
            try:
                # 동적으로 도구 모듈 import
                module_path = f"tools.{tool_name}.core"
                module = __import__(module_path, fromlist=["TOOL_MAP", "TOOL_SCHEMAS"])
                
                # 도구 함수와 스키마 가져오기
                tool_map = getattr(module, "TOOL_MAP", {})
                tool_schemas = getattr(module, "TOOL_SCHEMAS", [])
                
                # 도구 정보 저장
                self.loaded_tools[tool_name] = {
                    "functions": tool_map,
                    "schemas": tool_schemas
                }
                
                logger.info(f"도구 '{tool_name}' 로드 완료: {len(tool_map)}개 함수")
            except (ImportError, AttributeError) as e:
                logger.error(f"도구 '{tool_name}' 로드 실패: {str(e)}")
    
    def _handle_task_request(self, message: AgentMessage) -> Dict[str, Any]:
        """
        작업 요청 메시지를 처리합니다.
        
        Args:
            message: 처리할 메시지 객체
            
        Returns:
            처리 결과
        """
        try:
            task_data = message.content.get("task_data", {})
            response_data = {}
            
            # 작업 유형 검증
            task_type = task_data.get("type", "")
            if not task_type:
                raise ValidationError("작업 유형이 지정되지 않았습니다.", field="type")
                
            logger.info(f"이메일 작업 처리 시작: {task_type}")
            
            if task_type == "search_emails":
                # 이메일 검색 작업 처리
                keywords = task_data.get("keywords")
                subject = task_data.get("subject")
                date_on = task_data.get("date_on")
                date_after = task_data.get("date_after")
                date_before = task_data.get("date_before")
                mail_folder = task_data.get("mail_folder", "inbox")
                max_results = task_data.get("max_results", 10)
                
                # email_tool의 search_emails 함수 호출
                if "email_tool" in self.loaded_tools and "search_emails" in self.loaded_tools["email_tool"]["functions"]:
                    try:
                        # 지수 백오프를 사용한 재시도 로직 적용
                        def search_with_retry():
                            search_fn = self.loaded_tools["email_tool"]["functions"]["search_emails"]
                            result = search_fn(
                                keywords=keywords,
                                subject=subject,
                                date_on=date_on,
                                date_after=date_after,
                                date_before=date_before,
                                mail_folder=mail_folder,
                                max_results=max_results
                            )
                            if not result:
                                raise APIError("이메일 검색에 실패했습니다.", api_name="search_emails")
                            return result
                        
                        result = ErrorHandler.retry_with_backoff(
                            search_with_retry,
                            max_retries=3,
                            exceptions=(NetworkError, APIError)
                        )
                        response_data = result
                    except (NetworkError, APIError) as e:
                        logger.warning(f"이메일 검색 중 오류 발생: {str(e)}")
                        raise
                else:
                    raise APIError("search_emails 도구를 찾을 수 없습니다.", api_name="email_tool")
            
            elif task_type == "get_email_details":
                # 이메일 상세 조회 작업 처리
                email_id = task_data.get("email_id")
                mail_folder = task_data.get("mail_folder", "inbox")
                
                if not email_id:
                    raise ValidationError("이메일 ID가 제공되지 않았습니다.", field="email_id")
                
                # email_tool의 get_email_details 함수 호출
                if "email_tool" in self.loaded_tools and "get_email_details" in self.loaded_tools["email_tool"]["functions"]:
                    try:
                        # 지수 백오프를 사용한 재시도 로직 적용
                        def get_details_with_retry():
                            get_details_fn = self.loaded_tools["email_tool"]["functions"]["get_email_details"]
                            result = get_details_fn(email_id=email_id, mail_folder=mail_folder)
                            if not result:
                                raise APIError("이메일 상세 정보 조회에 실패했습니다.", api_name="get_email_details")
                            return result
                            
                        result = ErrorHandler.retry_with_backoff(
                            get_details_with_retry,
                            max_retries=3,
                            exceptions=(NetworkError, APIError)
                        )
                        response_data = result
                    except (NetworkError, APIError) as e:
                        logger.warning(f"이메일 상세 정보 조회 중 오류 발생: {str(e)}")
                        raise
                else:
                    raise APIError("get_email_details 도구를 찾을 수 없습니다.", api_name="email_tool")
            
            elif task_type == "generate_reply":
                subject = task_data.get("subject", "")
                body = task_data.get("body", "")
                sender = task_data.get("from", "")
                history = task_data.get("history", "")
                tone = task_data.get("tone", "")
                extra = task_data.get("extra_instruction", "")
                try:
                    from openai import OpenAI
                    import os
                    api_key = os.environ.get("OPENAI_API_KEY")
                    if not api_key:
                        raise Exception("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
                    client = OpenAI(api_key=api_key)
                    prompt = f"""
                    아래 메일에 대해 {tone}로 답장 초안을 작성해줘.\n[원본 메일 제목]: {subject}\n[원본 메일 본문]: {body}\n[발신자]: {sender}\n[과거 히스토리]: {history}\n[추가 지시사항]: {extra}\n답장 초안은 인사말, 본문, 마무리(감사합니다)까지 포함해서 자연스럽게 작성해줘.
                    """
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=500,
                        temperature=0.7,
                    )
                    reply = response.choices[0].message.content.strip()
                except Exception as e:
                    logger.error(f"LLM 답장 생성 실패: {e}")
                    reply = f"[LLM 답장 생성 실패] {e}"
                response_data = {"reply": reply}
            elif task_type == "send_reply":
                # 이메일 답장 작업 처리
                email_id = task_data.get("email_id")
                reply_body = task_data.get("reply_body")
                mail_folder = task_data.get("mail_folder", "inbox")
                
                if not email_id:
                    raise ValidationError("이메일 ID가 제공되지 않았습니다.", field="email_id")
                if not reply_body:
                    raise ValidationError("답장 내용이 제공되지 않았습니다.", field="reply_body")
                
                # email_tool의 send_reply 함수 호출
                if "email_tool" in self.loaded_tools and "send_reply" in self.loaded_tools["email_tool"]["functions"]:
                    try:
                        # 지수 백오프를 사용한 재시도 로직 적용
                        def send_reply_with_retry():
                            reply_fn = self.loaded_tools["email_tool"]["functions"]["send_reply"]
                            result = reply_fn(email_id=email_id, reply_body=reply_body, mail_folder=mail_folder)
                            if not result:
                                raise APIError("이메일 답장 전송에 실패했습니다.", api_name="send_reply")
                            return result
                            
                        result = ErrorHandler.retry_with_backoff(
                            send_reply_with_retry,
                            max_retries=3,
                            exceptions=(NetworkError, APIError)
                        )
                        response_data = result
                    except (NetworkError, APIError) as e:
                        logger.warning(f"이메일 답장 전송 중 오류 발생: {str(e)}")
                        raise
                else:
                    raise APIError("send_reply 도구를 찾을 수 없습니다.", api_name="email_tool")
            
            elif task_type == "save_attachments":
                # 이메일 첨부파일 저장 작업 처리
                email_id = task_data.get("email_id")
                save_path = task_data.get("save_path")
                mail_folder = task_data.get("mail_folder", "inbox")
                
                if not email_id:
                    raise ValidationError("이메일 ID가 제공되지 않았습니다.", field="email_id")
                if not save_path:
                    raise ValidationError("저장 경로가 제공되지 않았습니다.", field="save_path")
                
                # email_tool의 save_attachments 함수 호출
                if "email_tool" in self.loaded_tools and "save_attachments" in self.loaded_tools["email_tool"]["functions"]:
                    try:
                        # 지수 백오프를 사용한 재시도 로직 적용
                        def save_attachments_with_retry():
                            save_fn = self.loaded_tools["email_tool"]["functions"]["save_attachments"]
                            result = save_fn(email_id=email_id, save_path=save_path, mail_folder=mail_folder)
                            if not result:
                                raise APIError("첨부파일 저장에 실패했습니다.", api_name="save_attachments")
                            return result
                            
                        result = ErrorHandler.retry_with_backoff(
                            save_attachments_with_retry,
                            max_retries=3,
                            exceptions=(NetworkError, APIError)
                        )
                        response_data = result
                    except (NetworkError, APIError) as e:
                        logger.warning(f"첨부파일 저장 중 오류 발생: {str(e)}")
                        raise
                else:
                    raise APIError("save_attachments 도구를 찾을 수 없습니다.", api_name="email_tool")
            
            elif task_type == "get_daily_email_summary":
                # 일일 이메일 요약 작업 처리
                days_ago = task_data.get("days_ago", 0)
                mail_folder = task_data.get("mail_folder", "inbox")
                max_results = task_data.get("max_results", 20)
                
                # email_tool의 get_daily_email_summary 함수 호출
                if "email_tool" in self.loaded_tools and "get_daily_email_summary" in self.loaded_tools["email_tool"]["functions"]:
                    try:
                        # 지수 백오프를 사용한 재시도 로직 적용
                        def get_summary_with_retry():
                            summary_fn = self.loaded_tools["email_tool"]["functions"]["get_daily_email_summary"]
                            result = summary_fn(days_ago=days_ago, mail_folder=mail_folder, max_results=max_results)
                            if not result:
                                raise APIError("이메일 요약 생성에 실패했습니다.", api_name="get_daily_email_summary")
                            return result
                            
                        result = ErrorHandler.retry_with_backoff(
                            get_summary_with_retry,
                            max_retries=3,
                            exceptions=(NetworkError, APIError)
                        )
                        response_data = result
                    except (NetworkError, APIError) as e:
                        logger.warning(f"이메일 요약 생성 중 오류 발생: {str(e)}")
                        raise
                else:
                    raise APIError("get_daily_email_summary 도구를 찾을 수 없습니다.", api_name="email_tool")
            
            else:
                raise ValidationError(f"지원하지 않는 작업 유형입니다: {task_type}", field="type")
            
            # 응답 반환
            return {
                "status": "success",
                "task_id": message.content.get("task_id"),
                "result": response_data
            }
            
        except ValidationError as e:
            # 검증 오류 처리
            logger.warning(f"검증 오류: {str(e)}")
            context = {
                "agent_id": self.agent_id,
                "message_id": message.id,
                "task_type": message.content.get("task_data", {}).get("type", "")
            }
            return ErrorHandler.handle_error(e, context)
            
        except NetworkError as e:
            # 네트워크 오류 처리
            logger.warning(f"네트워크 오류: {str(e)}")
            context = {
                "agent_id": self.agent_id,
                "message_id": message.id
            }
            return ErrorHandler.handle_error(e, context)
            
        except APIError as e:
            # API 오류 처리
            logger.warning(f"API 오류: {str(e)}")
            context = {
                "agent_id": self.agent_id,
                "message_id": message.id,
                "api": getattr(e, "details", {}).get("api_name", "unknown")
            }
            return ErrorHandler.handle_error(e, context)
            
        except Exception as e:
            # 기타 예외 처리
            logger.error(f"예상치 못한 오류 발생: {str(e)}", exc_info=True)
            context = {
                "agent_id": self.agent_id,
                "message_id": message.id
            }
            return ErrorHandler.handle_error(e, context)
    
    def _handle_query(self, message: AgentMessage) -> Dict[str, Any]:
        """
        쿼리 메시지를 처리합니다.
        
        Args:
            message: 처리할 메시지 객체
            
        Returns:
            처리 결과
        """
        try:
            query = message.content.get("query", "")
            
            # 쿼리 검증
            if not query:
                raise ValidationError("쿼리가 제공되지 않았습니다.", field="query")
            
            # 쿼리 유형에 따라 처리
            if "tools" in query.lower() or "capabilities" in query.lower():
                # 지원하는 도구 및 기능 목록 반환
                available_tools = {}
                for tool_name, tool_data in self.loaded_tools.items():
                    available_tools[tool_name] = list(tool_data["functions"].keys())
                
                response_data = {
                    "status": "success",
                    "tools": available_tools
                }
            else:
                # 기본 에이전트 정보 반환
                response_data = {
                    "status": "success",
                    "agent_info": {
                        "name": self.name,
                        "id": self.id,
                        "specialization": self.specialization,
                        "capabilities": [
                            "이메일 검색",
                            "이메일 상세 조회",
                            "이메일 답장 보내기",
                            "이메일 첨부파일 저장",
                            "일일 이메일 요약"
                        ]
                    }
                }
            
            # 응답 반환
            return {
                "status": "success",
                "query_id": message.content.get("query_id"),
                "result": response_data
            }
            
        except ValidationError as e:
            # 검증 오류 처리
            logger.warning(f"쿼리 검증 오류: {str(e)}")
            context = {
                "agent_id": self.agent_id,
                "message_id": message.id,
                "query": message.content.get("query", "")
            }
            return ErrorHandler.handle_error(e, context)
            
        except Exception as e:
            # 기타 예외 처리
            logger.error(f"쿼리 처리 중 예상치 못한 오류 발생: {str(e)}", exc_info=True)
            context = {
                "agent_id": self.agent_id,
                "message_id": message.id,
                "query": message.content.get("query", "")
            }
            return ErrorHandler.handle_error(e, context)
