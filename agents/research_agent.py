import logging
from typing import Dict, List, Any, Optional
import json
import os
import sys
import importlib
import time

# .env 파일 로드 시도
try:
    from dotenv import load_dotenv
    load_dotenv()  # .env 파일에서 환경 변수 로드
    ENV_LOADED = True
except ImportError:
    ENV_LOADED = False
    logging.warning("python-dotenv library not found. Environment variables may not be loaded.")

# OpenAI 임포트 시도
try:
    import openai
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    logging.warning("OpenAI library not found. Some functions may not work.")

from .agent_base import BaseAgent
from .agent_protocol import MessageType

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ResearchAgent")

class ResearchAgent(BaseAgent):
    """
    연구 에이전트 클래스
    
    정보 수집, 검색, 관련 데이터 분석을 담당하는 전문 에이전트.
    웹 검색, 지식 베이스 쿼리 등의 도구를 활용하여 사용자 질문에 필요한
    정보를 수집하고 제공하는 역할을 수행
    """
    
    def __init__(self, agent_id: str = None, name: str = "Researcher",
                 specialization: str = "information_gathering", 
                 tools: List[str] = None):
        """
        연구 에이전트 초기화
        
        Args:
            agent_id: 에이전트 ID (없으면 자동 생성)
            name: 에이전트 이름
            specialization: 특화 영역 (기본값: information_gathering)
            tools: 사용 가능한 도구 목록
        """
        # 기본 도구 설정 (없으면)
        default_tools = ["web_search", "summarization_tool"]
        tools = tools or default_tools
        
        super().__init__(agent_id, name, specialization, tools)
        
        # 정보 캐시
        self.information_cache = {}
        # 현재 작업 컨텍스트
        self.current_context = {}
        
        # 메시지 유형별 처리 콜백 등록
        self.register_callback(MessageType.TASK_REQUEST.value, self._handle_task_request)
        self.register_callback(MessageType.QUERY.value, self._handle_query)
        
        logger.info(f"ResearchAgent initialized: {self.name} ({self.agent_id})")
        
        # 도구 모듈 로드 시도
        self._load_tools()
        
    def _load_tools(self):
        """각종 도구 모듈 로드"""
        self.loaded_tools = {}
        
        # 현재 디렉토리의 상위 디렉토리를 sys.path에 추가
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.append(parent_dir)
        
        # 도구 디렉토리 경로
        tools_dir = os.path.join(parent_dir, "tools")
        
        # 각 도구 모듈 로드 시도
        for tool_name in self.tools:
            try:
                # 도구 디렉토리에서 해당 도구 찾기
                tool_path = os.path.join(tools_dir, tool_name)
                if os.path.exists(tool_path):
                    # core.py 파일이 있는지 확인
                    core_file = os.path.join(tool_path, "core.py")
                    if os.path.exists(core_file):
                        # 도구 모듈 임포트
                        module_name = f"tools.{tool_name}.core"
                        try:
                            # 이미 임포트된 모듈인지 확인
                            if module_name in sys.modules:
                                tool_module = sys.modules[module_name]
                            else:
                                tool_module = importlib.import_module(module_name)
                                
                            # 필요한 함수가 있는지 확인
                            if tool_name == "summarization_tool" and hasattr(tool_module, "summarize_text"):
                                logger.info(f"Successfully loaded summarization_tool with summarize_text function")
                                
                            self.loaded_tools[tool_name] = tool_module
                            logger.info(f"Successfully loaded tool: {tool_name}")
                        except ImportError as ie:
                            logger.warning(f"Could not import {module_name}: {str(ie)}")
                    else:
                        logger.warning(f"Tool {tool_name} has no core.py file")
                else:
                    logger.warning(f"Tool directory for {tool_name} not found")
            except Exception as e:
                logger.error(f"Error loading tool {tool_name}: {str(e)}")
        
        logger.info(f"Loaded {len(self.loaded_tools)} tools: {list(self.loaded_tools.keys())}")
        
        # 필수 도구가 없는 경우 내장 기능 제공
        if "summarization_tool" not in self.loaded_tools and HAS_OPENAI:
            logger.info("Using built-in summarization capability")
            self.loaded_tools["summarization_tool"] = type('obj', (object,), {
                'summarize_text': self._built_in_summarize
            })
        
    def process_task(self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        작업 처리 메서드
        
        Args:
            task_data: 처리할 작업 데이터
            context: 추가 컨텍스트 정보
            
        Returns:
            처리 결과
        """
        logger.info(f"Processing task: {task_data.get('task_id', 'unknown')}")
        
        # 컨텍스트 정보 저장
        self.current_context = context or {}
        task_type = task_data.get('type', 'general_query')
        
        if task_type == "research":
            return self._process_research_task(task_data)
        elif task_type == "fact_check":
            return self._process_fact_check_task(task_data)
        else:
            # 기본 처리 로직
            return {
                "status": "not_supported",
                "message": f"Task type '{task_type}' not supported by {self.name}",
                "task_id": task_data.get('task_id', 'unknown')
            }
            
    def _process_research_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        연구 작업 처리
        
        Args:
            task_data: 연구 작업 데이터
            
        Returns:
            연구 결과
        """
        task_id = task_data.get('task_id', 'unknown')
        subtask_id = task_data.get('subtask_id', task_id)
        query = task_data.get('content', '')
        
        logger.info(f"Processing research task {subtask_id}: {query[:50]}...")
        
        # 정보 캐시에 이미 있는지 확인
        cache_key = f"query_{query.lower().replace(' ', '_')[:50]}"
        if cache_key in self.information_cache:
            logger.info(f"Using cached information for query: {query[:30]}...")
            return {
                "status": "success",
                "task_id": task_id,
                "subtask_id": subtask_id,
                "result": self.information_cache[cache_key]
            }
            
        # summarization_tool 도구가 있으면 사용
        if "summarization_tool" in self.loaded_tools:
            try:
                # 입력 검증 및 전처리
                processed_query = query.strip()
                if not processed_query:
                    return {
                        "status": "error",
                        "task_id": task_id,
                        "subtask_id": subtask_id,
                        "error": "Empty query"
                    }
                    
                # summarization_tool의 summarize_text 함수 호출
                logger.info(f"Using summarization_tool to process: {processed_query[:30]}...")
                
                # 프롬프트 템플릿 설정
                prompt_template = (
                    "당신은 정보 검색과 연구를 돕는 AI 연구원입니다. "
                    "다음 주제나 질문에 대해 상세한 정보와 사실을 조사하여 제공해주세요:\n\n"
                    "{text_to_summarize}\n\n"
                    "중요한 사실, 데이터, 주요 관점을 포함하여 종합적인 답변을 작성해주세요. "
                    "불확실한 정보는 명확히 표시하고, 가능하면 정보의 출처나 근거를 언급해주세요."
                )
                
                summarize_text = self.loaded_tools["summarization_tool"].summarize_text
                result = summarize_text(processed_query, prompt_template)
                
                if result.get("status") == "success":
                    # 결과 캐싱
                    self.information_cache[cache_key] = result
                    
                    return {
                        "status": "success",
                        "task_id": task_id,
                        "subtask_id": subtask_id,
                        "result": result
                    }
                else:
                    logger.error(f"Summarization tool error: {result.get('message')}")
                    return {
                        "status": "error",
                        "task_id": task_id,
                        "subtask_id": subtask_id,
                        "error": f"Summarization error: {result.get('message')}"
                    }
                    
            except Exception as e:
                logger.error(f"Error using summarization_tool: {str(e)}")
                return {
                    "status": "error",
                    "task_id": task_id,
                    "subtask_id": subtask_id,
                    "error": f"Tool execution error: {str(e)}"
                }
        else:
            # 도구가 없는 경우 내장 요약 기능 사용
            logger.info("Using built-in summarization capability instead of summarization_tool")
            
            # 입력 검증 및 전처리
            processed_query = query.strip()
            if not processed_query:
                return {
                    "status": "error",
                    "task_id": task_id,
                    "subtask_id": subtask_id,
                    "error": "Empty query"
                }
                
            # 프롬프트 템플릿 설정
            prompt_template = (
                "당신은 정보 검색과 연구를 도우는 AI 연구원입니다. "
                "다음 주제나 질문에 대해 상세한 정보와 사실을 조사하여 제공해주세요:\n\n"
                "{text_to_summarize}\n\n"
                "중요한 사실, 데이터, 주요 관점을 포함하여 종합적인 답변을 작성해주세요. "
                "불확실한 정보는 명확히 표시하고, 가능하면 정보의 출처나 근거를 언급해주세요."
            ) if not prompt_template else prompt_template
            
            # 내장 요약 기능 호출
            logger.info(f"Using built-in summarization for query: '{processed_query[:30]}...'")
            result = self._built_in_summarize(processed_query, prompt_template)
            logger.info(f"Built-in summarization result status: {result.get('status', 'unknown')}")
            
            if result.get("status") == "success":
                # 결과 캐싱
                self.information_cache[cache_key] = result
                
                return {
                    "status": "success",
                    "task_id": task_id,
                    "subtask_id": subtask_id,
                    "result": result
                }
            else:
                logger.error(f"Built-in summarization error: {result.get('error')}")
                return {
                    "status": "error",
                    "task_id": task_id,
                    "subtask_id": subtask_id,
                    "error": f"Summarization error: {result.get('error')}"
                }
            
    def _process_fact_check_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        사실 확인 작업 처리
        
        Args:
            task_data: 사실 확인 작업 데이터
            
        Returns:
            사실 확인 결과
        """
        task_id = task_data.get('task_id', 'unknown')
        subtask_id = task_data.get('subtask_id', task_id)
        statement = task_data.get('content', '')
        
        logger.info(f"Processing fact check task {subtask_id}: {statement[:50]}...")
        
        # TODO: 사실 확인 로직 구현
        # 현재는 기본 구현만 제공
        
        return {
            "status": "not_implemented",
            "task_id": task_id,
            "subtask_id": subtask_id,
            "message": "Fact checking functionality not fully implemented yet"
        }
        
    def _handle_task_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        작업 요청 메시지 처리
        
        Args:
            message: 받은 메시지
            
        Returns:
            처리 결과
        """
        sender_id = message.get('sender_id')
        content = message.get('content', {})
        
        logger.info(f"Received task request from {sender_id}")
        
        # content가 직접 task_data인 경우
        if isinstance(content, dict) and ('task_id' in content or 'content' in content):
            task_data = content
        else:
            # content에서 task_data 추출 필요
            task_data = {
                "task_id": message.get('message_id', 'unknown'),
                "content": content,
                "type": "research"  # 기본 타입
            }
            
        # 작업 처리
        result = self.process_task(task_data)
        
        return result
        
    def _handle_query(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        정보 조회 메시지 처리
        
        Args:
            message: 받은 메시지
            
        Returns:
            처리 결과
        """
        sender_id = message.get('sender_id')
        content = message.get('content', '')
        
        logger.info(f"Received query from {sender_id}: {content[:30]}...")
        
        # 조회 작업으로 변환하여 처리
        task_data = {
            "task_id": message.get('message_id', 'unknown'),
            "content": content,
            "type": "research",
            "query_source": "direct_query"
        }
        
        return self.process_task(task_data)
        
    def get_cached_information(self, query: str) -> Optional[Dict[str, Any]]:
        """
        캐시된 정보 조회
        
        Args:
            query: 검색어
            
        Returns:
            캐시된 정보 또는 None
        """
        cache_key = f"query_{query.lower().replace(' ', '_')[:50]}"
        return self.information_cache.get(cache_key)
    
    def _built_in_summarize(self, text_to_summarize: str, prompt_template: str = None) -> Dict[str, Any]:
        """
        내장 OpenAI 기반 요약 기능
        
        Args:
            text_to_summarize: 요약할 텍스트
            prompt_template: 프롬프트 템플릿 (없으면 기본값 사용)
            
        Returns:
            요약 결과와 상태를 포함한 디셔너리
        """
        if not HAS_OPENAI:
            self.logger.error("OpenAI library not available for built-in summarization")
            return {"status": "error", "error": "OpenAI library not available for summarization"}
        
        if not text_to_summarize or not text_to_summarize.strip():
            self.logger.warning("Empty text provided for summarization")
            return {"status": "error", "error": "Empty text provided"}
            
        # API 키 확인
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            self.logger.error("OPENAI_API_KEY not found in environment variables")
            return {"status": "error", "error": "API key not configured"}
        
        # 기본 프롬프트 템플릿
        default_template = (
            "당신은 정보 검색과 연구를 도우는 AI 연구원입니다. "
            "다음 주제나 질문에 대해 상세한 정보와 사실을 조사하여 제공해주세요:\n\n"
            "{text_to_summarize}\n\n"
            "중요한 사실, 데이터, 주요 관점을 포함하여 종합적인 답변을 작성해주세요. "
            "불확실한 정보는 명확히 표시하고, 가능하면 정보의 출처나 근거를 언급해주세요."
        )
        
        # 사용할 프롬프트 템플릿 결정
        template_to_use = prompt_template or default_template
        
        # 프롬프트 준비
        full_prompt = template_to_use.format(text_to_summarize=text_to_summarize)
        
        # 재시도 명 사이의 대기 시간
        wait_times = [1, 2, 4]  # 지수적으로 증가
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "사용자가 제공한 텍스트를 요약하는 도우미입니다."}, 
                        {"role": "user", "content": full_prompt}
                    ],
                    max_tokens=1000,
                    temperature=0.3,
                )
                
                return {"status": "success", "summary": response.choices[0].message.content.strip()}
                
            except Exception as e:
                self.logger.error(f"OpenAI API error (attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:  # 마지막 시도가 아니면 대기
                    time.sleep(wait_times[min(attempt, len(wait_times)-1)])
        
        return {"status": "error", "error": "Failed to summarize text after multiple attempts"}

def _process_fact_check_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    사실 확인 작업 처리

    Args:
        task_data: 사실 확인 작업 데이터

    Returns:
        사실 확인 결과
    """
    task_id = task_data.get('task_id', 'unknown')
    subtask_id = task_data.get('subtask_id', task_id)
    statement = task_data.get('content', '')

    logger.info(f"Processing fact check task {subtask_id}: {statement[:50]}...")

    # TODO: 사실 확인 로직 구현
    # 현재는 기본 구현만 제공

    return {
        "status": "not_implemented",
        "task_id": task_id,
        "subtask_id": subtask_id,
        "message": "Fact checking functionality not fully implemented yet"
    }

def _handle_task_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
    """
    작업 요청 메시지 처리

    Args:
        message: 받은 메시지

    Returns:
        처리 결과
    """
    sender_id = message.get('sender_id')
    content = message.get('content', {})

    logger.info(f"Received task request from {sender_id}")

    # content가 직접 task_data인 경우
    if isinstance(content, dict) and ('task_id' in content or 'content' in content):
        task_data = content
    else:
        # content에서 task_data 추출 필요
        task_data = {
            "task_id": message.get('message_id', 'unknown'),
            "content": content,
            "type": "research"  # 기본 타입
        }

    # 작업 처리
    result = self.process_task(task_data)

    return result

def _handle_query(self, message: Dict[str, Any]) -> Dict[str, Any]:
    """
    정보 조회 메시지 처리

    Args:
        message: 받은 메시지

    Returns:
        처리 결과
    """
    sender_id = message.get('sender_id')
    content = message.get('content', '')

    logger.info(f"Received query from {sender_id}: {content[:30]}...")

    # 조회 작업으로 변환하여 처리
    task_data = {
        "task_id": message.get('message_id', 'unknown'),
        "content": content,
        "type": "research",
        "query_source": "direct_query"
    }

    return self.process_task(task_data)

def get_cached_information(self, query: str) -> Optional[Dict[str, Any]]:
    """
    캐시된 정보 조회

    Args:
        query: 검색어

    Returns:
        캐시된 정보 또는 None
    """
    cache_key = f"query_{query.lower().replace(' ', '_')[:50]}"
    return self.information_cache.get(cache_key)

def _built_in_summarize(self, text: str, max_retries: int = 3) -> Dict[str, Any]:
    """
    외부 요약 도구에 대한 내장형 폴백 기능

    Args:
        text: 요약하고자 하는 텍스트
        max_retries: 오류 발생시 재시도 횟수

    Returns:
        요약 결과
    """
    if not HAS_OPENAI:
        self.logger.error("OpenAI library not available for built-in summarization")
        return {"status": "error", "error": "OpenAI library not available for summarization"}

    if not text or not text.strip():
        self.logger.warning("Empty text provided for summarization")
        return {"status": "error", "error": "Empty text provided"}

    # API 키 확인
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        self.logger.error("OPENAI_API_KEY not found in environment variables")
        return {"status": "error", "error": "API key not configured"}

    prompt = f"""
    다음 텍스트를 간결히 요약해주세요:

    ---
    {text}
    ---

    요약:
    """

    # 재시도 명 사이의 대기 시간
    wait_times = [1, 2, 4]  # 지수적으로 증가

    for attempt in range(max_retries):
        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "사용자가 제공한 텍스트를 요약하는 도우미입니다."}, 
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3,
            )

            return {"status": "success", "summary": response.choices[0].message.content.strip()}

        except Exception as e:
            self.logger.error(f"OpenAI API error (attempt {attempt+1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:  # 마지막 시도가 아니면 대기
                time.sleep(wait_times[min(attempt, len(wait_times)-1)])

    return {"status": "error", "error": "Failed to summarize text after multiple attempts"}
