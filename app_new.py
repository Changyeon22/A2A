#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
My AI Agent - 멀티 에이전트 AI 시스템 (모듈화 버전)

음성 인식, 이메일 처리, 기획서 작성 등 다양한 AI 기능을 제공하는 
통합 에이전트 시스템의 메인 Streamlit 애플리케이션입니다.
"""

import sys
import os

# 프로젝트 모듈 임포트를 위한 경로 설정
current_script_dir = os.path.dirname(os.path.abspath(__file__))
if current_script_dir not in sys.path:
    sys.path.insert(0, current_script_dir)

# 하위 모듈 경로 추가
for subdir in ["tools", "ui_components", "agents", "app"]:
    subdir_path = os.path.join(current_script_dir, subdir)
    if subdir_path not in sys.path:
        sys.path.insert(0, subdir_path)

# 새로운 모듈화된 앱 임포트
from app.main import main

if __name__ == "__main__":
    main() 