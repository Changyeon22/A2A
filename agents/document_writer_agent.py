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
logger = logging.getLogger("DocumentWriterAgent")

class DocumentWriterAgent(BaseAgent):
    """
    문서 작성 에이전트 클래스
    
    문서 작성, 편집, 포맷팅을 담당하는 전문 에이전트.
    연구 결과나 사용자 요청을 바탕으로 구조화된 문서를 생성하고
    다양한 형식으로 출력하는 역할을 수행
    """
    
    def __init__(self, agent_id: str = None, name: str = "DocumentWriter",
                 specialization: str = "document_writing", 
                 tools: List[str] = None):
        """
        문서 작성 에이전트 초기화
        
        Args:
            agent_id: 에이전트 ID (없으면 자동 생성)
            name: 에이전트 이름
            specialization: 전문 영역
            tools: 사용할 도구 목록
        """
        # 기본 에이전트 초기화
        super().__init__(agent_id=agent_id, name=name, specialization=specialization)
        
        # 문서 캐시: 이미 작성된 문서 저장
        self.document_cache = {}
        
        # 도구 로드
        self.loaded_tools = {}
        
        # 기본 도구 목록
        if tools is None:
            # 기본적으로 document_formatter와 template_generator 도구를 로드
            tools = ["document_formatter", "template_generator"]
        
        self.load_tools(tools)
        
        # 문서 템플릿 저장
        self.document_templates = {
            "report": {
                "title": "# {title}\n\n",
                "summary": "## 요약\n\n{summary}\n\n",
                "introduction": "## 서론\n\n{introduction}\n\n",
                "body": "## 본론\n\n{body}\n\n",
                "conclusion": "## 결론\n\n{conclusion}\n\n",
                "references": "## 참고 문헌\n\n{references}\n\n"
            },
            "article": {
                "title": "# {title}\n\n",
                "introduction": "{introduction}\n\n",
                "sections": "{sections}\n\n",
                "conclusion": "{conclusion}\n\n"
            },
            "memo": {
                "title": "# {title}\n\n",
                "content": "{content}\n\n",
                "notes": "---\n\n**노트:** {notes}\n\n"
            },
            "research": {
                "title": "# {title}: 연구 보고서\n\n",
                "abstract": "## 초록\n\n{abstract}\n\n",
                "methodology": "## 연구 방법\n\n{methodology}\n\n",
                "findings": "## 연구 결과\n\n{findings}\n\n",
                "discussion": "## 논의\n\n{discussion}\n\n",
                "references": "## 참고 문헌\n\n{references}\n\n"
            }
        }
        
        # 메시지 핸들러 등록
        self.register_callback(MessageType.TASK_REQUEST.value, self._handle_task_request)
        self.register_callback(MessageType.QUERY.value, self._handle_query)

    def load_tools(self, tool_names: List[str]) -> None:
        """
        지정된 도구를 로드합니다.
        
        Args:
            tool_names: 로드할 도구 이름 리스트
        """
        for tool_name in tool_names:
            try:
                # 도구 디렉토리 확인
                tool_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", tool_name)
                
                if not os.path.isdir(tool_dir):
                    logger.warning(f"Tool directory for {tool_name} not found")
                    continue
                    
                # 도구 모듈 로드 시도
                module_path = f"tools.{tool_name}.core"
                module = importlib.import_module(module_path)
                
                # 도구 함수 저장
                if tool_name == "document_formatter" and hasattr(module, "format_document"):
                    self.loaded_tools[tool_name] = module
                    logger.info(f"Successfully loaded tool: {tool_name}")
                elif tool_name == "template_generator" and hasattr(module, "generate_template"):
                    self.loaded_tools[tool_name] = module
                    logger.info(f"Successfully loaded tool: {tool_name}")
                else:
                    logger.info(f"Loaded {tool_name}, but no supported functions found")
                    
            except ImportError as e:
                logger.warning(f"Could not import {module_path}: {str(e)}")
            except Exception as e:
                logger.error(f"Error loading tool {tool_name}: {str(e)}")
                
        logger.info(f"Loaded {len(self.loaded_tools)} tools: {list(self.loaded_tools.keys())}")
        
        # 도구가 없는 경우 내장 기능 사용
        if not any(tool in self.loaded_tools for tool in ["document_formatter", "template_generator"]):
            logger.info("Using built-in document writing capability")

    def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        태스크 처리
        
        Args:
            task_data: 태스크 데이터
            
        Returns:
            태스크 처리 결과
        """
        task_type = task_data.get("type", "")
        
        if task_type == "document_creation":
            return self._process_document_creation_task(task_data)
        elif task_type == "document_editing":
            return self._process_document_editing_task(task_data)
        elif task_type == "template_selection":
            return self._process_template_selection_task(task_data)
        else:
            # 기본 처리 로직
            return {
                "status": "not_supported",
                "message": f"Task type '{task_type}' not supported by {self.name}",
                "task_id": task_data.get('task_id', 'unknown')
            }
            
    def _process_document_creation_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        문서 생성 작업 처리
        
        Args:
            task_data: 문서 생성 작업 데이터
            
        Returns:
            문서 생성 결과
        """
        task_id = task_data.get('task_id', 'unknown')
        subtask_id = task_data.get('subtask_id', task_id)
        document_type = task_data.get('document_type', 'report')
        content = task_data.get('content', {})
        title = content.get('title', '문서 제목')
        
        logger.info(f"Processing document creation task {subtask_id}: {title}")
        
        # 정보 캐시에 이미 있는지 확인
        cache_key = f"doc_{document_type}_{title.lower().replace(' ', '_')[:30]}"
        if cache_key in self.document_cache:
            logger.info(f"Using cached document for title: {title}")
            return {
                "status": "success",
                "task_id": task_id,
                "subtask_id": subtask_id,
                "result": self.document_cache[cache_key]
            }
        
        # 문서 생성
        try:
            # 매개변수에서 청크 플래그를 확인
            use_chunking = task_data.get('use_chunking', False)
            max_chunk_size = task_data.get('max_chunk_size', 4000)  # 기본 4000자
            
            # document_formatter 도구가 있으면 사용
            if "document_formatter" in self.loaded_tools:
                logger.info(f"Using document_formatter tool for document: {title}")
                format_document = self.loaded_tools["document_formatter"].format_document
                result = format_document(document_type, content)
            else:
                # 내장 문서 생성 기능 사용
                logger.info(f"Using built-in document creation for: {title}")
                
                if use_chunking:
                    logger.info(f"Using chunked document creation with max_chunk_size={max_chunk_size}")
                    result = self._create_document_with_chunking(document_type, content, max_chunk_size)
                else:
                    result = self._create_document(document_type, content)
                
            if result.get("status") == "success":
                # 결과 캐싱
                self.document_cache[cache_key] = result
                
                return {
                    "status": "success",
                    "task_id": task_id,
                    "subtask_id": subtask_id,
                    "result": result
                }
            else:
                logger.error(f"Document creation error: {result.get('message')}")
                return {
                    "status": "error",
                    "task_id": task_id,
                    "subtask_id": subtask_id,
                    "error": f"Document creation error: {result.get('message')}"
                }
                
        except Exception as e:
            logger.error(f"Error creating document: {str(e)}")
            return {
                "status": "error",
                "task_id": task_id,
                "subtask_id": subtask_id,
                "error": f"Document creation error: {str(e)}"
            }
            
    def _create_document(self, document_type: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        내장 문서 생성 기능
        
        Args:
            document_type: 문서 유형 ('report', 'article' 등)
            content: 문서 내용
            
        Returns:
            문서 생성 결과
        """
        if document_type not in self.document_templates:
            return {
                "status": "error",
                "message": f"Unknown document type: {document_type}"
            }
            
        template = self.document_templates[document_type]
        document = ""
        
        # 템플릿에 따라 문서 생성
        for section, section_template in template.items():
            if section in content:
                section_content = content.get(section, "")
                document += section_template.format(**{section: section_content})
                
        if not document:
            return {
                "status": "error",
                "message": "Failed to create document: no content provided"
            }
            
        return {
            "status": "success",
            "document": document,
            "document_type": document_type,
            "title": content.get("title", "문서 제목")
        }
        
    def _process_document_editing_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        문서 편집 작업 처리
        
        Args:
            task_data: 문서 편집 작업 데이터
            
        Returns:
            문서 편집 결과
        """
        task_id = task_data.get('task_id', 'unknown')
        subtask_id = task_data.get('subtask_id', task_id)
        document_id = task_data.get('document_id', '')
        edit_type = task_data.get('edit_type', 'modify')  # modify, append, format 등
        content = task_data.get('content', {})
        
        logger.info(f"Processing document editing task {subtask_id}: {edit_type} for {document_id}")
        
        # 문서가 캐시에 있는지 확인
        if document_id not in self.document_cache:
            logger.error(f"Document {document_id} not found in cache")
            return {
                "status": "error",
                "task_id": task_id,
                "subtask_id": subtask_id,
                "error": f"Document {document_id} not found"
            }
            
        original_doc = self.document_cache[document_id]
        document_type = original_doc.get('document_type', 'report')
        
        try:
            if edit_type == "modify":
                # 부분 수정
                section = content.get('section', '')
                new_content = content.get('content', '')
                
                # 원본 문서 내용을 수정
                doc_content = original_doc.get('document', '')
                if section and new_content:
                    # 간단한 문서 서식 처리를 통한 수정
                    # 실제로는 더 복잡한 처리가 필요하겠지만 예제로 간단히 구현
                    section_header = f"## {section}"
                    parts = doc_content.split(section_header)
                    
                    if len(parts) >= 2:
                        # 헤더를 찾았으면 다음 섹션까지의 내용을 교체
                        next_section_pos = parts[1].find("##")
                        if next_section_pos > -1:
                            parts[1] = f"\n\n{new_content}\n\n" + parts[1][next_section_pos:]
                        else:
                            parts[1] = f"\n\n{new_content}\n\n"
                            
                        modified_doc = section_header.join(parts)
                    else:
                        # 헤더가 없으면 끝에 추가
                        modified_doc = doc_content + f"\n\n{section_header}\n\n{new_content}\n\n"
                else:
                    # 섹션을 지정하지 않으면 전체 교체
                    modified_doc = new_content
                    
                result = {
                    "status": "success",
                    "document": modified_doc,
                    "document_type": document_type,
                    "title": original_doc.get("title", "문서 제목"),
                    "edit_type": "modify"
                }
                
            elif edit_type == "append":
                # 끝에 콘텐츠 추가
                appendix = content.get('content', '')
                doc_content = original_doc.get('document', '')
                modified_doc = doc_content + "\n\n" + appendix
                
                result = {
                    "status": "success",
                    "document": modified_doc,
                    "document_type": document_type,
                    "title": original_doc.get("title", "문서 제목"),
                    "edit_type": "append"
                }
                
            elif edit_type == "format":
                # 포맷 변경 - 실제 적용하려면 더 복잡한 가공이 필요
                new_format = content.get('format', 'markdown')
                doc_content = original_doc.get('document', '')
                
                # 간단한 마크다운 포맷팅
                if new_format == 'markdown':
                    # 이미 마크다운이므로 그대로 유지
                    modified_doc = doc_content
                else:
                    # 현재는 마크다운만 지원
                    modified_doc = doc_content
                    
                result = {
                    "status": "success",
                    "document": modified_doc,
                    "document_type": document_type,
                    "title": original_doc.get("title", "문서 제목"),
                    "format": new_format,
                    "edit_type": "format"
                }
            else:
                # 지원하지 않는 편집 타입
                logger.error(f"Unsupported edit type: {edit_type}")
                return {
                    "status": "error",
                    "task_id": task_id,
                    "subtask_id": subtask_id,
                    "error": f"Unsupported edit type: {edit_type}"
                }
                
            # 결과 캐싱 & 반환
            self.document_cache[document_id] = result
            return {
                "status": "success",
                "task_id": task_id,
                "subtask_id": subtask_id,
                "result": result
            }
                
        except Exception as e:
            logger.error(f"Error editing document: {str(e)}")
            return {
                "status": "error",
                "task_id": task_id,
                "subtask_id": subtask_id,
                "error": f"Document editing error: {str(e)}"
            }
            
    def _process_template_selection_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        템플릿 선택 작업 처리
        
        Args:
            task_data: 템플릿 선택 작업 데이터
            
        Returns:
            템플릿 선택 결과
        """
        task_id = task_data.get('task_id', 'unknown')
        subtask_id = task_data.get('subtask_id', task_id)
        template_type = task_data.get('template_type', 'report')
        
        logger.info(f"Processing template selection task {subtask_id}: {template_type}")
        
        try:
            # template_generator 도구가 있으면 사용
            if "template_generator" in self.loaded_tools and hasattr(self.loaded_tools["template_generator"], "generate_template"):
                logger.info(f"Using template_generator tool for template type: {template_type}")
                generate_template = self.loaded_tools["template_generator"].generate_template
                result = generate_template(template_type)
            else:
                # 내장 템플릿 사용
                logger.info(f"Using built-in template for type: {template_type}")
                
                if template_type in self.document_templates:
                    template = self.document_templates[template_type]
                    result = {
                        "status": "success",
                        "template": template,
                        "template_type": template_type
                    }
                else:
                    logger.error(f"Template type {template_type} not found")
                    return {
                        "status": "error",
                        "task_id": task_id,
                        "subtask_id": subtask_id,
                        "error": f"Template type {template_type} not found"
                    }
                    
            return {
                "status": "success",
                "task_id": task_id,
                "subtask_id": subtask_id,
                "result": result
            }
                
        except Exception as e:
            logger.error(f"Error selecting template: {str(e)}")
            return {
                "status": "error",
                "task_id": task_id,
                "subtask_id": subtask_id,
                "error": f"Template selection error: {str(e)}"
            }
            
    def _handle_task_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        작업 요청 메시지 처리
        
        Args:
            message: 받은 메시지
            
        Returns:
            처리 결과
        """
        logger.info(f"Processing task: {message.get('task_id', 'unknown')}")
        
        # 작업 지침 추출
        task_data = message.get('task_data', {})
        
        # 태스크 처리
        result = self.process_task(task_data)
        
        # 결과 반환
        response = {
            "type": "task_response",
            "status": result.get("status", "error"),
            "task_id": task_data.get("task_id"),
            "agent_id": self.agent_id
        }
        
        # 결과나 오류 정보 추가
        if result.get("status") == "success":
            response["result"] = result.get("result")
        else:
            response["error"] = result.get("error", "Unknown error")
            
        return response
        
    def _handle_query(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        정보 조회 메시지 처리
        
        Args:
            message: 받은 메시지
            
        Returns:
            처리 결과
        """
        query_type = message.get('query_type', '')
        query = message.get('query', '')
        query_id = message.get('query_id', 'unknown')
        
        logger.info(f"Processing query: {query_id}, type: {query_type}")
        
        response = {
            "type": "query_response",
            "query_id": query_id,
            "agent_id": self.agent_id
        }
        
        if query_type == "available_templates":
            # 사용 가능한 템플릿 목록 조회
            response["status"] = "success"
            response["result"] = {
                "templates": list(self.document_templates.keys())
            }
        elif query_type == "document_cache":
            # 문서 캐시 조회
            cache_keys = list(self.document_cache.keys())
            cache_info = [
                {
                    "id": key,
                    "title": self.document_cache[key].get("title", "Unknown"),
                    "type": self.document_cache[key].get("document_type", "Unknown")
                } for key in cache_keys
            ]
            response["status"] = "success"
            response["result"] = {
                "documents": cache_info
            }
        elif query_type == "document_by_id" and query:
            # 특정 문서 조회
            if query in self.document_cache:
                response["status"] = "success"
                response["result"] = {
                    "document": self.document_cache[query]
                }
            else:
                response["status"] = "error"
                response["error"] = f"Document {query} not found"
        else:
            response["status"] = "error"
            response["error"] = f"Unknown query type: {query_type}"
            
        return response
        
    def get_document_by_id(self, document_id: str) -> Dict[str, Any]:
        """
        문서 ID로 문서 조회
        
        Args:
            document_id: 문서 ID
            
        Returns:
            문서 데이터 또는 빈 디터너리
        """
        return self.document_cache.get(document_id, {})
        
    def generate_document_chunked(self, document_type: str, content: Dict[str, Any], 
                                max_chunk_size: int = 4000) -> Dict[str, Any]:
        """
        긴 문서를 청크 단위로 나누어 생성하는 기능
        
        Args:
            document_type: 문서 유형
            content: 문서 내용
            max_chunk_size: 최대 청크 크기 (문자 수)
            
        Returns:
            문서 생성 결과
        """
        logger.info(f"Generating chunked document of type: {document_type}")
        
        if document_type not in self.document_templates:
            return {
                "status": "error",
                "message": f"Unknown document type: {document_type}"
            }
            
        # 미리 섹션 분할
        template = self.document_templates[document_type]
        sections = list(template.keys())
        chunked_document = {}
        chunked_result = []
        current_chunk = ""
        current_chunk_sections = []
        
        for section in sections:
            if section not in content:
                continue
                
            section_content = content.get(section, "")
            section_text = template[section].format(**{section: section_content})
            
            # 현재 청크에 섹션을 추가했을 때 최대 크기 초과 여부 확인
            if len(current_chunk) + len(section_text) <= max_chunk_size:
                current_chunk += section_text
                current_chunk_sections.append(section)
            else:
                # 현재 청크가 최대 크기를 초과하면 청크 저장 및 새 청크 시작
                if current_chunk:
                    chunk_id = str(uuid.uuid4())
                    chunked_result.append({
                        "chunk_id": chunk_id,
                        "content": current_chunk,
                        "sections": current_chunk_sections,
                        "size": len(current_chunk)
                    })
                    
                # 새 청크 시작
                current_chunk = section_text
                current_chunk_sections = [section]
                
            # 매우 긴 단일 섹션은 추가 분할 필요
            if len(section_text) > max_chunk_size:
                # 현재 청크를 저장
                if current_chunk and current_chunk != section_text:
                    chunk_id = str(uuid.uuid4())
                    chunked_result.append({
                        "chunk_id": chunk_id,
                        "content": current_chunk,
                        "sections": current_chunk_sections,
                        "size": len(current_chunk)
                    })
                
                # 긴 섹션을 문장 단위로 분할
                paragraphs = section_text.split("\n\n")
                temp_chunk = ""
                temp_sections = [f"{section} (part)"]
                
                for paragraph in paragraphs:
                    if len(temp_chunk) + len(paragraph) + 2 <= max_chunk_size:
                        if temp_chunk:
                            temp_chunk += "\n\n" + paragraph
                        else:
                            temp_chunk = paragraph
                    else:
                        # 현재 단락 문장들 저장
                        if temp_chunk:
                            chunk_id = str(uuid.uuid4())
                            chunked_result.append({
                                "chunk_id": chunk_id,
                                "content": temp_chunk,
                                "sections": temp_sections,
                                "size": len(temp_chunk),
                                "is_partial": True
                            })
                        
                        # 새 부분 시작
                        temp_chunk = paragraph
                
                # 마지막 부분 처리
                if temp_chunk:
                    chunk_id = str(uuid.uuid4())
                    chunked_result.append({
                        "chunk_id": chunk_id,
                        "content": temp_chunk,
                        "sections": temp_sections,
                        "size": len(temp_chunk),
                        "is_partial": True
                    })
                    
                # 청크 처리가 끝났으므로 다시 초기화
                current_chunk = ""
                current_chunk_sections = []
        
        # 마지막 청크 처리
        if current_chunk:
            chunk_id = str(uuid.uuid4())
            chunked_result.append({
                "chunk_id": chunk_id,
                "content": current_chunk,
                "sections": current_chunk_sections,
                "size": len(current_chunk)
            })
            
        # 문서 및 메타데이터 구성
        full_document = "".join([chunk["content"] for chunk in chunked_result])
        document_id = str(uuid.uuid4())
        metadata = {
            "document_id": document_id,
            "title": content.get("title", "문서 제목"),
            "document_type": document_type,
            "total_chunks": len(chunked_result),
            "total_size": len(full_document),
            "chunks": chunked_result
        }
        
        # 결과 반환
        return {
            "status": "success",
            "document": full_document,
            "document_id": document_id,
            "document_type": document_type,
            "title": content.get("title", "문서 제목"),
            "metadata": metadata,
            "is_chunked": True
        }
        
    def _create_document_with_chunking(self, document_type: str, content: Dict[str, Any], 
                                     max_chunk_size: int = 4000) -> Dict[str, Any]:
        """
        청크를 사용하는 문서 생성 함수
        
        Args:
            document_type: 문서 유형
            content: 문서 내용
            max_chunk_size: 최대 청크 크기
            
        Returns:
            문서 생성 결과
        """
        # 일반 문서 생성 시도
        result = self._create_document(document_type, content)
        
        # 생성된 문서가 일정 크기(기본 4000자) 넓으면 청크로 분할
        if result.get("status") == "success" and len(result.get("document", "")) > max_chunk_size:
            logger.info(f"Document exceeds {max_chunk_size} characters, using chunking method")
            # 청크 기반 생성 시도
            return self.generate_document_chunked(document_type, content, max_chunk_size)
        
        return result
