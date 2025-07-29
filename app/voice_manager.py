#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
음성 처리 관리 모듈

음성 인식, 음성 합성, 음성 관련 기능을 관리합니다.
"""

import streamlit as st
import speech_recognition as sr
import threading
import time
from typing import Dict, Any, Optional, Callable
import logging

from .types import VoiceConfig, AIResponse
from tools.voice_tool.core import speech_to_text_from_mic_data

logger = logging.getLogger(__name__)

class VoiceManager:
    """음성 처리 관리 클래스"""
    
    def __init__(self, session_manager) -> None:
        """VoiceManager 초기화"""
        self.session_manager = session_manager
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.voice_config: VoiceConfig = {
            "language": "ko-KR",
            "timeout": 5.0,
            "phrase_time_limit": 10.0,
            "continuous": False
        }
        self._setup_microphone()
        logger.info("VoiceManager 초기화 완료")
    
    def _setup_microphone(self) -> None:
        """마이크 설정"""
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            logger.info("마이크 설정 완료")
        except Exception as e:
            logger.error(f"마이크 설정 실패: {e}")
    
    def get_voice_input_once(self) -> Optional[str]:
        """한 번의 음성 입력 처리"""
        try:
            with self.microphone as source:
                logger.info("음성 입력 대기 중...")
                audio = self.recognizer.listen(
                    source, 
                    timeout=self.voice_config["timeout"],
                    phrase_time_limit=self.voice_config["phrase_time_limit"]
                )
                
                logger.info("음성 인식 중...")
                text = self.recognizer.recognize_google(
                    audio, 
                    language=self.voice_config["language"]
                )
                
                logger.info(f"음성 인식 결과: {text}")
                return text
                
        except sr.WaitTimeoutError:
            logger.warning("음성 입력 시간 초과")
            return None
        except sr.UnknownValueError:
            logger.warning("음성을 인식할 수 없습니다")
            return None
        except sr.RequestError as e:
            logger.error(f"음성 인식 서비스 오류: {e}")
            return None
        except Exception as e:
            logger.error(f"음성 입력 처리 중 오류: {e}")
            return None
    
    def start_continuous_voice_recognition(self) -> None:
        """연속 음성 인식 시작"""
        if self.session_manager.is_voice_recognition_active():
            logger.warning("이미 음성 인식이 활성화되어 있습니다")
            return
        
        self.session_manager.set_voice_recognition_active(True)
        voice_thread = threading.Thread(
            target=self._continuous_voice_listener,
            daemon=True
        )
        self.session_manager.set_voice_thread(voice_thread)
        voice_thread.start()
        logger.info("연속 음성 인식 시작")
    
    def stop_continuous_voice_recognition(self) -> None:
        """연속 음성 인식 중지"""
        if not self.session_manager.is_voice_recognition_active():
            logger.warning("음성 인식이 활성화되어 있지 않습니다")
            return
        
        self.session_manager.set_voice_recognition_active(False)
        voice_thread = self.session_manager.get_voice_thread()
        if voice_thread and voice_thread.is_alive():
            # 스레드 종료 신호 전송
            pass
        
        logger.info("연속 음성 인식 중지")
    
    def _continuous_voice_listener(self) -> None:
        """연속 음성 인식 리스너"""
        try:
            while self.session_manager.is_voice_recognition_active():
                try:
                    with self.microphone as source:
                        audio = self.recognizer.listen(
                            source, 
                            timeout=1.0,
                            phrase_time_limit=self.voice_config["phrase_time_limit"]
                        )
                        
                        text = self.recognizer.recognize_google(
                            audio, 
                            language=self.voice_config["language"]
                        )
                        
                        if text.strip():
                            logger.info(f"연속 음성 인식: {text}")
                            # 세션에 텍스트 입력 설정
                            self.session_manager.set_text_input(text)
                            # UI 업데이트를 위한 rerun 트리거
                            st.rerun()
                            
                except sr.WaitTimeoutError:
                    # 타임아웃은 정상적인 상황
                    continue
                except sr.UnknownValueError:
                    # 음성 인식 실패는 무시
                    continue
                except Exception as e:
                    logger.error(f"연속 음성 인식 중 오류: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"연속 음성 인식 스레드 오류: {e}")
        finally:
            self.session_manager.set_voice_recognition_active(False)
    
    def process_voice_input(self) -> Optional[str]:
        """음성 입력 처리 (UI에서 호출)"""
        if not self.session_manager.is_voice_recognition_active():
            return self.get_voice_input_once()
        else:
            # 연속 모드에서는 이미 처리된 텍스트 반환
            return self.session_manager.get_text_input()
    
    def play_audio_in_browser(self, audio_bytes: bytes) -> None:
        """브라우저에서 오디오 재생"""
        if not audio_bytes:
            return
        
        try:
            import base64
            audio_base64 = base64.b64encode(audio_bytes).decode()
            audio_html = f"""
                <audio autoplay style="display:none">
                    <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mpeg">
                </audio>
            """
            st.markdown(audio_html, unsafe_allow_html=True)
            logger.debug("오디오 재생 완료")
        except Exception as e:
            logger.error(f"오디오 재생 실패: {e}")
    
    def set_voice_config(self, config: VoiceConfig) -> None:
        """음성 설정 변경"""
        self.voice_config.update(config)
        logger.info(f"음성 설정 업데이트: {config}")
    
    def get_voice_config(self) -> VoiceConfig:
        """현재 음성 설정 반환"""
        return self.voice_config.copy()
    
    def is_voice_available(self) -> bool:
        """음성 기능 사용 가능 여부 확인"""
        try:
            # 마이크 접근 가능 여부 확인
            with self.microphone as source:
                pass
            return True
        except Exception as e:
            logger.error(f"음성 기능 사용 불가: {e}")
            return False
    
    def get_voice_status(self) -> Dict[str, Any]:
        """음성 상태 정보 반환"""
        return {
            "is_active": self.session_manager.is_voice_recognition_active(),
            "is_available": self.is_voice_available(),
            "config": self.get_voice_config(),
            "thread_alive": (
                self.session_manager.get_voice_thread() is not None and 
                self.session_manager.get_voice_thread().is_alive()
            )
        }
    
    def handle_voice_error(self, error: Exception) -> None:
        """음성 관련 오류 처리"""
        error_message = str(error)
        
        if "timeout" in error_message.lower():
            logger.warning("음성 입력 시간 초과")
        elif "unknown" in error_message.lower():
            logger.warning("음성을 인식할 수 없습니다")
        elif "request" in error_message.lower():
            logger.error("음성 인식 서비스 오류")
        else:
            logger.error(f"음성 처리 오류: {error_message}")
        
        # UI에 오류 메시지 표시
        st.error(f"음성 처리 오류: {error_message}")
    
    def cleanup(self) -> None:
        """음성 관리자 정리"""
        self.stop_continuous_voice_recognition()
        logger.info("VoiceManager 정리 완료")
    
    def process_ai_response_audio(self, response: AIResponse) -> None:
        """AI 응답의 오디오 처리"""
        if not response.get("audio_content"):
            return
        
        try:
            # 오디오 재생
            self.play_audio_in_browser(response["audio_content"])
            
            # 음성 텍스트가 있으면 세션에 저장
            if response.get("voice_text"):
                self.session_manager.add_assistant_message(
                    content=response.get("text_content", ""),
                    voice_text=response["voice_text"],
                    detailed_text=response.get("detailed_text")
                )
            else:
                # 일반 텍스트 응답
                self.session_manager.add_assistant_message(
                    content=response.get("text_content", "")
                )
                
        except Exception as e:
            logger.error(f"AI 응답 오디오 처리 실패: {e}")
            self.handle_voice_error(e)
    
    def get_voice_metrics(self) -> Dict[str, Any]:
        """음성 관련 메트릭 반환"""
        # 실제 구현에서는 더 상세한 메트릭을 수집할 수 있음
        return {
            "voice_recognition_count": 0,  # 음성 인식 횟수
            "voice_synthesis_count": 0,    # 음성 합성 횟수
            "average_recognition_time": 0.0,  # 평균 인식 시간
            "error_count": 0,              # 오류 횟수
            "uptime": time.time()          # 가동 시간
        } 