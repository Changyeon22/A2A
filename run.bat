@echo off
REM run.bat - AI 기획 비서 Streamlit 앱 실행 스크립트

REM 현재 디렉토리로 이동 (스크립트가 어디서 실행되든 프로젝트 루트로 이동)
cd /d "%~dp0"

REM Streamlit 앱 실행
python -m streamlit run app.py

pause