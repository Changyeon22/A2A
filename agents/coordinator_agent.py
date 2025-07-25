import logging
from typing import Dict, List, Any, Optional
import json
import os

# .env 파일 로드 시도
try:
    from dotenv import load_dotenv
    load_dotenv()  # .env 파일에서 환경 변수 로드
    ENV_LOADED = True
except ImportError:
    ENV_LOADED = False
    logging.warning("python-dotenv library not found. Environment variables may not be loaded.")

from .agent_base import BaseAgent
from .agent_protocol import MessageType, AgentMessage

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CoordinatorAgent")

class CoordinatorAgent(BaseAgent):
    """
    조정자 에이전트 클래스
    
    사용자 요청을 분석하고 적절한 하위 작업으로 분할한 후
    전문 에이전트에게 작업을 할당하고 결과를 수집하는 역할
    """
    
    def __init__(self, agent_id: str = None, name: str = "Coordinator",
                 specialization: str = "task_coordination", tools: List[str] = None):
        """
        조정자 에이전트 초기화
        
        Args:
            agent_id: 에이전트 ID (없으면 자동 생성)
            name: 에이전트 이름
            specialization: 특화 영역 (기본값: task_coordination)
            tools: 사용 가능한 도구 목록
        """
        super().__init__(agent_id, name, specialization, tools)
        self.task_queue = []
        self.active_tasks = {}
        self.task_assignments = {}  # 작업 ID와 할당된 에이전트 매핑
        self.task_results = {}  # 작업 ID와 결과 매핑
        
        # 메시지 유형별 처리 콜백 등록
        self.register_callback(MessageType.TASK_RESPONSE.value, self._handle_task_response)
        self.register_callback(MessageType.STATUS_UPDATE.value, self._handle_status_update)
        self.register_callback(MessageType.ERROR.value, self._handle_error)
        
        logger.info(f"CoordinatorAgent initialized: {self.name} ({self.agent_id})")
        
    def process_task(self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        사용자 요청 처리 메서드
        
        Args:
            task_data: 처리할 작업 데이터 (사용자 요청)
            context: 추가 컨텍스트 정보
            
        Returns:
            처리 결과 또는 진행 상태
        """
        logger.info(f"Processing task: {task_data.get('task_id', 'unknown')}")
        
        # 작업 유형에 따라 다른 처리 로직
        task_type = task_data.get('type', 'general_request')
        
        if task_type == 'user_request':
            return self._process_user_request(task_data, context)
        elif task_type == 'subtask_assignment':
            return self._handle_subtask_assignment(task_data, context)
        elif task_type == 'result_collection':
            return self._handle_result_collection(task_data, context)
        else:
            # 기본 처리 로직
            return {
                "status": "acknowledged",
                "message": f"Task received by {self.name}",
                "task_id": task_data.get('task_id', 'unknown')
            }
            
    def _process_user_request(self, task_data: Dict[str, Any], 
                             context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        사용자 요청 분석 및 하위 작업 분할
        """
        user_request = task_data.get('content', '')
        task_id = task_data.get('task_id', 'unknown')
        logger.info(f"Processing user request for task {task_id}: {str(user_request)[:50]}...")

        # --- 이메일 워크플로우 분할/분배 ---
        if isinstance(user_request, dict) and user_request.get('type') == 'email_workflow':
            email_body = user_request.get('email_body', '')
            attachments = user_request.get('attachments', [])
            history = user_request.get('history', [])
            # 실제 Agent 인스턴스는 agent_manager 등에서 주입받는다고 가정
            mail_summary_agent = context.get('mail_summary_agent') if context else None
            mail_analysis_agent = context.get('mail_analysis_agent') if context else None
            mail_attachment_agent = context.get('mail_attachment_agent') if context else None
            mail_context_agent = context.get('mail_context_agent') if context else None
            mail_reply_agent = context.get('mail_reply_agent') if context else None
            results = {}
            # 1. 요약
            if mail_summary_agent:
                results['summary'] = mail_summary_agent.process_task({'email_body': email_body})
            # 2. 분석
            if mail_analysis_agent:
                results['analysis'] = mail_analysis_agent.process_task({'email_body': email_body})
            # 3. 첨부파일
            if mail_attachment_agent and attachments:
                results['attachments'] = mail_attachment_agent.process_task({'attachments': attachments})
            # 4. 대화 히스토리 분석 (자동 답장 등)
            if mail_context_agent and history:
                context_result = mail_context_agent.process_task({'history': history})
                results['context'] = context_result
                # 5. 답장 초안 (히스토리 분석 결과 활용)
                if mail_reply_agent:
                    results['reply'] = mail_reply_agent.process_task({'email_body': email_body, 'context': context_result.get('context', '')})
            elif mail_reply_agent:
                # 히스토리 없이 답장 초안만 생성
                results['reply'] = mail_reply_agent.process_task({'email_body': email_body})
            return {
                'status': 'completed',
                'message': '이메일 워크플로우 처리 완료',
                'task_id': task_id,
                'results': results
            }
        # --- 기존 일반 워크플로우 ---
        # TODO: LLM을 사용하여 요청을 분석하고 하위 작업으로 분할
        # 현재는 직접 하위 작업을 정의하는 간단한 구현
        
        # 임시 하위 작업 정의 (실제로는 LLM이 생성)
        subtasks = [
            {
                "subtask_id": f"{task_id}_research",
                "type": "research",
                "description": "사용자 요청에 관련된 정보 조사",
                "content": f"다음 주제에 대한 정보를 조사하세요: {user_request}",
                "priority": "medium"
            },
            {
                "subtask_id": f"{task_id}_analysis",
                "type": "analysis",
                "description": "정보 분석 및 인사이트 도출",
                "content": f"조사된 정보를 분석하고 핵심 인사이트를 도출하세요",
                "priority": "medium",
                "depends_on": [f"{task_id}_research"]
            }
        ]
        
        # 하위 작업 저장
        self.update_memory(f"subtasks_{task_id}", subtasks)
        self.update_memory(f"original_request_{task_id}", user_request)
        
        return {
            "status": "subtasks_created",
            "message": f"User request analyzed and split into {len(subtasks)} subtasks",
            "task_id": task_id,
            "subtasks": subtasks
        }
        
    def _handle_subtask_assignment(self, task_data: Dict[str, Any],
                                  context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        하위 작업 할당 처리
        
        Args:
            task_data: 작업 할당 데이터
            context: 추가 컨텍스트 정보
            
        Returns:
            할당 결과
        """
        task_id = task_data.get('task_id')
        subtask_id = task_data.get('subtask_id')
        agent_id = task_data.get('agent_id')
        
        logger.info(f"Assigning subtask {subtask_id} to agent {agent_id}")
        
        # 작업 할당 정보 저장
        if task_id not in self.task_assignments:
            self.task_assignments[task_id] = {}
            
        self.task_assignments[task_id][subtask_id] = {
            "agent_id": agent_id,
            "status": "assigned",
            "assigned_at": task_data.get('timestamp')
        }
        
        return {
            "status": "assigned",
            "message": f"Subtask {subtask_id} assigned to agent {agent_id}",
            "task_id": task_id,
            "subtask_id": subtask_id
        }
        
    def _handle_result_collection(self, task_data: Dict[str, Any],
                                 context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        작업 결과 수집 처리
        
        Args:
            task_data: 결과 수집 데이터
            context: 추가 컨텍스트 정보
            
        Returns:
            수집 결과
        """
        task_id = task_data.get('task_id')
        
        # 원래 사용자 요청 가져오기
        original_request = self.get_memory(f"original_request_{task_id}", "")
        
        # 모든 하위 작업 결과 수집
        all_results = {}
        errors_found = False
        
        for subtask_id, result in self.task_results.get(task_id, {}).items():
            all_results[subtask_id] = result
            
            # 오류 확인
            if isinstance(result, dict) and "error" in result:
                logger.warning(f"Error in subtask {subtask_id}: {result['error']}")
                errors_found = True
        
        # Fallback 응답 생성
        fallback_message = None
        
        # 수집된 결과가 없거나 오류가 있는 경우 fallback 응답 생성
        if not all_results or errors_found:
            fallback_message = self._generate_fallback_response(original_request, task_id)
            
        # 결과가 전혀 없는 경우
        if not all_results:
            return {
                "status": "no_results",
                "message": f"No results available for task {task_id}",
                "task_id": task_id,
                "fallback_message": fallback_message,
                "original_request": original_request
            }
            
        # 결과 반환
        return {
            "status": "results_collected",
            "message": f"Results collected for task {task_id}",
            "task_id": task_id,
            "results": all_results,
            "fallback_message": fallback_message,
            "original_request": original_request
        }
        
    def _handle_task_response(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        작업 응답 메시지 처리 (다른 에이전트로부터)
        
        Args:
            message: 받은 메시지
            
        Returns:
            처리 결과
        """
        sender_id = message.get('sender_id')
        content = message.get('content', {})
        task_id = content.get('task_id')
        subtask_id = content.get('subtask_id')
        result = content.get('result')
        
        logger.info(f"Received task response from {sender_id} for subtask {subtask_id}")
        
        # 결과 저장
        if task_id not in self.task_results:
            self.task_results[task_id] = {}
            
        self.task_results[task_id][subtask_id] = result
        
        # 작업 상태 업데이트
        if task_id in self.task_assignments and subtask_id in self.task_assignments[task_id]:
            self.task_assignments[task_id][subtask_id]["status"] = "completed"
            
        return {
            "status": "result_recorded",
            "message": f"Result for subtask {subtask_id} received and recorded",
            "task_id": task_id,
            "subtask_id": subtask_id
        }
        
    def _handle_status_update(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        상태 업데이트 메시지 처리
        
        Args:
            message: 받은 메시지
            
        Returns:
            처리 결과
        """
        sender_id = message.get('sender_id')
        content = message.get('content', {})
        task_id = content.get('task_id')
        subtask_id = content.get('subtask_id')
        status = content.get('status')
        
        logger.info(f"Status update from {sender_id}: {subtask_id} is {status}")
        
        # 작업 상태 업데이트
        if (task_id in self.task_assignments and 
            subtask_id in self.task_assignments[task_id]):
            self.task_assignments[task_id][subtask_id]["status"] = status
            
        return {
            "status": "update_acknowledged",
            "message": f"Status update for {subtask_id} acknowledged",
            "task_id": task_id,
            "subtask_id": subtask_id
        }
        
    def _generate_fallback_response(self, original_request: str, task_id: str) -> str:
        """
        에이전트가 작업을 완료할 수 없는 경우를 위한 기본 응답 생성
        
        Args:
            original_request: 원래 사용자 요청
            task_id: 작업 ID
            
        Returns:
            기본 응답 메시지
        """
        logger.info(f"Generating fallback response for task {task_id}")
        
        # 요청이 비어 있는지 확인
        if not original_request or not original_request.strip():
            return "죄송합니다, 요청을 처리할 수 없습니다. 다른 질문을 해주실래요?"
        
        # OpenAI 사용 가능한지 확인
        try:
            from openai import OpenAI
            has_openai = True
        except ImportError:
            has_openai = False
            logger.warning("OpenAI library not available for fallback response generation")
        
        # OpenAI를 사용하여 기본 응답 생성
        if has_openai:
            try:
                # API 키 없을 경우를 위한 확인
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    logger.warning("OPENAI_API_KEY not found in environment variables")
                    return f"지금 귀하의 질문 '{original_request[:50]}...'에 대한 검색 결과를 찾을 수 없습니다. 필요한 구성이 완료되면 다시 시도해주세요."
                
                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4",  # 또는 다른 적절한 모델
                    messages=[
                        {"role": "system", "content": "당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 가능한 한 정확하고 도움이 되는 정보로 응답해주세요."}, 
                        {"role": "user", "content": f"다음 질문에 대해 가장 정확하고 도움이 되는 정보를 제공해주세요: {original_request}"}
                    ],
                    max_tokens=1000,
                    temperature=0.7,
                )
                
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"Error generating fallback response with OpenAI: {str(e)}")
        
        # 오류 또는 OpenAI가 없는 경우 기본 응답 사용
        return f"죄송합니다, 현재 귀하의 질문 '{original_request[:50]}...'(에) 대한 답변을 처리하는 도중 문제가 발생했습니다. 다른 질문을 해주시거나 잠시 후 다시 시도해 주세요."
    
    def _handle_error(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        오류 메시지 처리
        
        Args:
            message: 받은 메시지
            
        Returns:
            처리 결과
        """
        sender_id = message.get('sender_id')
        content = message.get('content', {})
        task_id = content.get('task_id')
        subtask_id = content.get('subtask_id')
        error = content.get('error', 'Unknown error')
        
        logger.error(f"Received error from {sender_id} for task {task_id}, subtask {subtask_id}: {error}")
        
        # 작업 상태 업데이트
        if task_id:
            if task_id in self.active_tasks:
                self.active_tasks[task_id]['status'] = 'error'
                self.active_tasks[task_id]['error'] = error
                
            if task_id in self.task_assignments and subtask_id in self.task_assignments[task_id]:
                self.task_assignments[task_id][subtask_id]['status'] = 'error'
                self.task_assignments[task_id][subtask_id]['error'] = error
                
            # 작업 결과 저장
            if task_id not in self.task_results:
                self.task_results[task_id] = {}
                
            self.task_results[task_id][subtask_id] = {
                "status": "error",
                "error": error
            }
        
        return {
            "status": "error_handled",
            "message": f"Error from {sender_id} for task {task_id}, subtask {subtask_id} handled",
            "task_id": task_id,
            "subtask_id": subtask_id
        }
        
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        작업 상태 조회
        
        Args:
            task_id: 작업 ID
            
        Returns:
            작업 상태 정보
        """
        # 원본 요청 정보
        original_request = self.get_memory(f"original_request_{task_id}", "")
        
        # 하위 작업 정보
        subtasks = self.get_memory(f"subtasks_{task_id}", [])
        
        # 할당 상태
        assignments = self.task_assignments.get(task_id, {})
        
        # 결과 정보
        results = self.task_results.get(task_id, {})
        
        # 전체 작업 완료 여부 확인
        all_completed = all(
            assignments.get(subtask["subtask_id"], {}).get("status") == "completed"
            for subtask in subtasks
        ) if subtasks and assignments else False
        
        return {
            "task_id": task_id,
            "original_request": original_request,
            "subtasks": subtasks,
            "assignments": assignments,
            "results": results,
            "all_completed": all_completed,
            "status": "completed" if all_completed else "in_progress"
        }

    def process_prompt_workflow(self, user_input: str, options: Dict[str, Any], domain: str = '일반', mode: str = 'basic') -> Dict[str, Any]:
        """
        프롬프트 자동화 전체 워크플로우 (A2A 구조 기반)
        1. PromptEngineerAgent → 2. DomainExpertAgent → 3. QAAssistantAgent
        mode: 'basic' 또는 'advanced'에 따라 프롬프트 엔지니어 페르소나가 달라짐
        """
        from .prompt_engineer_agent import PromptEngineerAgent
        from .domain_expert_agent import DomainExpertAgent
        from .qa_assistant_agent import QAAssistantAgent
        import streamlit as st

        # 1. 프롬프트 초안 생성
        if hasattr(st.session_state, 'current_process'):
            st.session_state.current_process = {"type": "prompt", "desc": "프롬프트 초안 생성 중...", "progress": 0.2}
        prompt_engineer = PromptEngineerAgent()
        draft_result = prompt_engineer.process_task({'user_input': user_input, 'options': options, 'mode': mode})
        draft_prompt = draft_result.get('prompt', '')

        # 2. 도메인 전문가 피드백
        if hasattr(st.session_state, 'current_process'):
            st.session_state.current_process = {"type": "prompt", "desc": "도메인 피드백/보완 중...", "progress": 0.5}
        domain_expert = DomainExpertAgent()
        domain_result = domain_expert.process_task({'prompt': draft_prompt, 'domain': domain})
        improved_prompt = domain_result.get('suggested_prompt', draft_prompt)
        feedback = domain_result.get('feedback', '')

        # 3. QA 평가
        if hasattr(st.session_state, 'current_process'):
            st.session_state.current_process = {"type": "prompt", "desc": "QA 평가/개선점 도출 중...", "progress": 0.8}
        qa_assistant = QAAssistantAgent()
        qa_result = qa_assistant.process_task({'prompt': improved_prompt})

        # 결과 취합
        # --- 최종 프롬프트 자동 생성 단계 ---
        try:
            from openai import OpenAI
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                client = OpenAI(api_key=api_key)
                system_prompt = "너는 프롬프트 엔지니어이자 QA 평가자야. 아래 초안, 도메인 피드백, QA 피드백을 모두 반영해 최고의 프롬프트를 만들어줘."
                user_prompt = f"""
[초안]\n{draft_prompt}\n\n[도메인 피드백]\n{feedback}\n\n[QA 피드백]\n{qa_result.get('review', '')}\n{qa_result.get('improvement', '')}\n\n위 모든 내용을 반영해, 목적에 가장 부합하고 명확하며, 실제 사용에 적합한 최종 프롬프트를 제안해줘.\n"""
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=1200,
                    temperature=0.7,
                )
                final_prompt = response.choices[0].message.content.strip()
            else:
                final_prompt = improved_prompt
        except Exception as e:
            final_prompt = improved_prompt
        return {
            'draft_prompt': draft_prompt,
            'engineer_rationale': draft_result.get('rationale', ''),
            'domain_feedback': feedback,
            'improved_prompt': improved_prompt,
            'qa_score': qa_result.get('score', 0),
            'qa_review': qa_result.get('review', ''),
            'qa_improvement': qa_result.get('improvement', ''),
            'final_prompt': final_prompt
        }

    def plan_and_execute_workflow(self, user_command: str, context: dict = None) -> dict:
        """
        유저의 자연어 복합 명령을 LLM을 통해 단계별로 분해하고, 각 단계별로 적합한 Agent/Tool을 매핑하여 순차 실행하는 고도화 워크플로우 함수.
        """
        import os
        from openai import OpenAI
        import re
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return {"status": "error", "message": "OpenAI API 키가 설정되어 있지 않습니다."}
        client = OpenAI(api_key=api_key)
        # 1. LLM에 분해 프롬프트 전달
        system_prompt = """
너는 AI 멀티에이전트 코디네이터야. 아래 유저 명령을 단계별로 분해하고, 각 단계별로 사용할 Agent/Tool을 아래 포맷으로 설계해줘.

[예시]
1. DataAnalysisTool: 엑셀 파일 분석
2. InsightExtractor: 인사이트 요약
3. DocumentWriterAgent: 보고서 자동 작성
4. EmailAgent: 보고서 이메일 발송

[유저 명령]
"""
        user_prompt = f"{user_command}\n\n위 명령을 반드시 위 예시 포맷처럼 단계별로 분해해서 답변해줘."
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000,
            temperature=0.3,
        )
        plan_text = response.choices[0].message.content.strip()
        # 2. 단계별 파싱
        step_pattern = re.compile(r"(\d+)\.\s*([A-Za-z0-9_]+):\s*(.+)")
        steps = []
        for match in step_pattern.finditer(plan_text):
            steps.append({
                "step": int(match.group(1)),
                "agent": match.group(2),
                "desc": match.group(3)
            })
        if not steps:
            return {"status": "error", "message": f"분해 실패: {plan_text}"}
        # 3. 단계별 실행
        results = []
        last_output = None
        for step in steps:
            agent = step["agent"]
            desc = step["desc"]
            try:
                # 실제 Agent/Tool 호출 분기 (간단 예시, 실제 프로젝트에 맞게 확장 필요)
                if agent == "DataAnalysisTool":
                    # context에 파일 등 입력 필요
                    if context and "uploaded_file" in context:
                        from tools.data_analysis import DataAnalysisTool
                        tool = DataAnalysisTool()
                        result = tool.process_uploaded_file(context["uploaded_file"])
                        last_output = result
                    else:
                        result = {"error": "분석 파일이 필요합니다."}
                elif agent == "InsightExtractor":
                    if last_output and "data" in last_output:
                        from tools.data_analysis import InsightExtractor
                        extractor = InsightExtractor()
                        result = extractor.extract_insights(last_output["data"])
                        last_output = result
                    else:
                        result = {"error": "이전 단계 데이터가 필요합니다."}
                elif agent == "DocumentWriterAgent":
                    # 예시: 보고서 자동 작성 (실제 구현에 맞게 수정)
                    if last_output and "insights" in last_output:
                        # 실제 문서 생성 함수 호출 필요
                        result = {"report": f"보고서: {last_output['insights']}"}
                        last_output = result
                    else:
                        result = {"error": "인사이트 데이터가 필요합니다."}
                elif agent == "EmailAgent":
                    # 예시: 이메일 발송 (실제 구현에 맞게 수정)
                    if last_output and "report" in last_output:
                        # 실제 이메일 발송 함수 호출 필요
                        result = {"email_status": f"이메일 발송 완료: {last_output['report']}"}
                        last_output = result
                    else:
                        result = {"error": "보고서 데이터가 필요합니다."}
                else:
                    result = {"error": f"알 수 없는 Agent/Tool: {agent}"}
            except Exception as e:
                result = {"error": f"{agent} 실행 중 오류: {str(e)}"}
            results.append({"step": step["step"], "agent": agent, "desc": desc, "result": result})
        return {
            "status": "success",
            "plan": steps,
            "results": results,
            "final_output": last_output
        }
