from .agent_base import BaseAgent
from tools.prompt_tool.core import qa_evaluate_prompt
from typing import Dict, Any

class QAAssistantAgent(BaseAgent):
    """
    QA 평가자 역할: 프롬프트 품질 평가/개선점 제안 담당
    """
    def process_task(self, task_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        prompt = task_data.get('prompt', '')
        return qa_evaluate_prompt(prompt) 