# 개발 가이드 📚

## 프로젝트 설정

### 1. 개발 환경 설정

```bash
# 저장소 클론
git clone <repository-url>
cd my_ai_agent

# 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# 개발 의존성 설치
pip install -e .[dev,test]

# Pre-commit 훅 설치
pre-commit install
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 필요한 API 키를 설정하세요:

```env
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
NOTION_TOKEN=your_notion_token_here
```

## 테스트 프레임워크

### 테스트 실행 명령어

```bash
# 모든 테스트 실행
pytest tests/ -v

# 단위 테스트만
pytest tests/unit/ -v

# 통합 테스트만  
pytest tests/integration/ -v

# 커버리지 포함
pytest tests/ --cov=. --cov-report=html

# 특정 테스트 실행
pytest tests/unit/test_config.py::TestConfig::test_config_initialization -v
```

### 새로운 테스트 작성

#### 단위 테스트 템플릿

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from unittest.mock import Mock, patch, MagicMock

class TestYourModule:
    """YourModule 단위 테스트"""
    
    def test_your_function(self):
        """함수 테스트"""
        # Given
        input_data = "test_input"
        
        # When
        result = your_function(input_data)
        
        # Then
        assert result is not None
        assert isinstance(result, dict)
```

#### 통합 테스트 템플릿

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from unittest.mock import patch

@pytest.mark.integration
class TestYourIntegration:
    """통합 테스트"""
    
    def test_integration_workflow(self):
        """워크플로우 통합 테스트"""
        # 여러 컴포넌트가 함께 작동하는지 테스트
        pass
```

## 코드 품질 도구

### 자동 포맷팅

```bash
# Black으로 코드 포맷팅
black .

# isort로 import 정렬
isort .

# 둘 다 함께 실행
black . && isort .
```

### 코드 분석

```bash
# Flake8으로 린팅
flake8 . --max-line-length=88 --extend-ignore=E203,W503

# MyPy로 타입 검사
mypy agents/ tools/ config.py

# 모든 품질 검사 실행
pre-commit run --all-files
```

## 프로젝트 구조 가이드

### 새로운 에이전트 추가

1. **에이전트 클래스 생성**
```python
# agents/your_new_agent.py
from agents.agent_base import BaseAgent

class YourNewAgent(BaseAgent):
    def __init__(self, agent_id: str = None, name: str = "YourSpecialist"):
        super().__init__(agent_id=agent_id, name=name, 
                        specialization="your_domain")
    
    def process_task(self, task_data: dict) -> dict:
        """작업 처리 로직"""
        pass
```

2. **테스트 작성**
```python
# tests/unit/test_your_new_agent.py
def test_your_new_agent_creation():
    agent = YourNewAgent(agent_id="test_agent")
    assert agent.agent_id == "test_agent"
    assert agent.name == "YourSpecialist"
```

### 새로운 도구 추가

1. **도구 디렉토리 구조**
```
tools/your_new_tool/
├── __init__.py
├── core.py         # 메인 기능
├── configs.py      # 설정
└── utils.py        # 유틸리티 함수
```

2. **도구 구현**
```python
# tools/your_new_tool/core.py
def your_tool_function(param1: str, param2: int) -> dict:
    """도구 함수 구현"""
    return {"status": "success", "result": "your_result"}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "your_tool_function",
            "description": "도구 설명",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1": {"type": "string"},
                    "param2": {"type": "integer"}
                },
                "required": ["param1", "param2"]
            }
        }
    }
]

TOOL_MAP = {
    "your_tool_function": your_tool_function
}
```

## CI/CD 파이프라인

### GitHub Actions

프로젝트는 다음 워크플로우를 포함합니다:

- **테스트**: Python 3.8-3.11에서 모든 테스트 실행
- **코드 품질**: Black, isort, flake8, mypy 검사
- **커버리지**: Codecov에 커버리지 리포트 업로드
- **빌드**: 메인 브랜치에서 패키지 빌드

### 로컬 개발 워크플로우

```bash
# 1. 기능 브랜치 생성
git checkout -b feature/your-feature

# 2. 코드 작성 및 테스트
pytest tests/ -v

# 3. 코드 품질 검사
pre-commit run --all-files

# 4. 커밋 및 푸시
git add .
git commit -m "feat: add your feature"
git push origin feature/your-feature
```

## 디버깅 가이드

### 로깅 설정

```python
import logging

# 로거 생성
logger = logging.getLogger(__name__)

# 디버그 정보 출력
logger.debug("디버그 메시지")
logger.info("정보 메시지")
logger.warning("경고 메시지")
logger.error("오류 메시지")
```

### 일반적인 문제해결

1. **테스트 실패**
   - `pytest tests/ -v --tb=long`으로 자세한 오류 확인
   - 모킹이 올바르게 설정되었는지 확인

2. **Import 오류**
   - `sys.path` 설정 확인
   - `__init__.py` 파일 존재 확인

3. **API 키 관련 오류**
   - `.env` 파일 설정 확인
   - 환경 변수 로드 확인

## 성능 최적화

### 테스트 성능

```bash
# 병렬 테스트 실행
pytest tests/ -n auto

# 빠른 실패 모드
pytest tests/ -x

# 느린 테스트 제외
pytest tests/ -m "not slow"
```

### 코드 프로파일링

```python
import cProfile
import pstats

# 함수 프로파일링
cProfile.run('your_function()', 'profile_output')
stats = pstats.Stats('profile_output')
stats.sort_stats('time').print_stats(10)
```

## 배포 가이드

### 패키지 빌드

```bash
# 빌드 도구 설치
pip install build

# 패키지 빌드
python -m build

# 빌드 결과 확인
ls dist/
```

### 버전 관리

`pyproject.toml`에서 버전을 업데이트하고 태그를 생성:

```bash
git tag v1.1.0
git push origin v1.1.0
```

## 기여 가이드

1. **이슈 생성**: 새로운 기능이나 버그 리포트
2. **브랜치 생성**: `feature/` 또는 `bugfix/` 접두사 사용
3. **테스트 작성**: 새로운 코드에는 반드시 테스트 포함
4. **문서 업데이트**: README.md 및 관련 문서 업데이트
5. **Pull Request**: 코드 리뷰 요청

## 참고 자료

- [Pytest 공식 문서](https://docs.pytest.org/)
- [Black 코드 포맷터](https://black.readthedocs.io/)
- [Pre-commit 훅](https://pre-commit.com/)
- [MyPy 타입 체커](https://mypy.readthedocs.io/)
