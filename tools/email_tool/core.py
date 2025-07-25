import logging
import traceback
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import os # Added missing import for os

from .auth import get_credentials, get_imap_connection, get_smtp_connection
from .utils import clean_header, get_email_body
from .configs import (
    DEFAULT_MAIL_FOLDER, DEFAULT_MAX_RESULTS,
    STATUS_SUCCESS, STATUS_ERROR,
    ERROR_CREDENTIALS_NOT_CONFIGURED, ERROR_EMPTY_SEARCH_QUERY,
    ERROR_FETCH_EMAIL, ERROR_EMAIL_NOT_FOUND, ERROR_NO_ATTACHMENTS,
    ERROR_SEARCH_FAILED, ERROR_INVALID_DATE_FORMAT,
    SUCCESS_REPLY_SENT, SUCCESS_ATTACHMENT_SAVED,
    SUCCESS_NO_EMAILS_FOUND, SUCCESS_NO_EMAILS_ON_DATE
)

# --- 로거 설정 ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- Main Tool Functions ---
def search_emails(keywords: Optional[List[str]] = None, subject: Optional[str] = None, date_on: Optional[str] = None, date_after: Optional[str] = None, date_before: Optional[str] = None, mail_folder: str = DEFAULT_MAIL_FOLDER, max_results: int = DEFAULT_MAX_RESULTS) -> Dict[str, Any]:
    """
    사용자의 Gmail 계정에서 고급 조건으로 이메일을 검색합니다.
    키워드, 제목, 날짜 범위(특정일, 이후, 이전)로 필터링할 수 있습니다.
    한국어 및 기타 UTF-8 문자를 완벽하게 지원합니다.
    
    Args:
        keywords (Optional[List[str]]): 이메일 본문이나 제목에서 검색할 키워드 목록
        subject (Optional[str]): 이메일 제목에서 특별히 검색할 키워드
        date_on (Optional[str]): 특정 날짜에 대한 검색 (예: 'YYYY/MM/DD')
        date_after (Optional[str]): 검색 범위의 시작 날짜 (예: 'YYYY/MM/DD')
        date_before (Optional[str]): 검색 범위의 종료 날짜 (예: 'YYYY/MM/DD')
        mail_folder (str): 검색할 메일 폴더, 기본값은 'inbox'
        max_results (int): 반환할 최대 이메일 수, 기본값은 10
        
    Returns:
        Dict[str, Any]: 검색 결과를 포함하는 딕셔너리
    """
    try:
        # 인증 정보 확인
        try:
            gmail_address, _ = get_credentials()
        except ValueError:
            return {"status": STATUS_ERROR, "error": ERROR_CREDENTIALS_NOT_CONFIGURED}
        
        # 검색어 확인
        if not keywords and not subject:
            logger.warning("검색어가 비어 있습니다")
            return {"status": STATUS_ERROR, "error": ERROR_EMPTY_SEARCH_QUERY}

        # IMAP 연결
        mail = get_imap_connection()
        mail.select(mail_folder)

        # --- Gmail의 X-GM-RAW 속성을 위한 검색 쿼리 구성 ---
        query_parts = []
        if subject:
            # 큰따옴표 대신 괄호를 사용하여 중첩 따옴표 문제를 근본적으로 방지
            # Gmail 검색에서 괄호는 구문 그룹화에 사용되어 더 안정적
            query_parts.append(f'subject:({subject})')
        if keywords:
            query_parts.append(' '.join(keywords))

        # --- 날짜 처리 로직 ---
        if date_on:
            try:
                # 'YYYY/MM/DD' 또는 'YYYY-MM-DD' 형식의 날짜를 파싱
                on_date = datetime.strptime(date_on.replace('/', '-'), '%Y-%m-%d')
                # 안정적인 after/before 쿼리로 변환
                after_date = on_date - timedelta(days=1)
                before_date = on_date + timedelta(days=1)
                query_parts.append(f'after:{after_date.strftime("%Y-%m-%d")} before:{before_date.strftime("%Y-%m-%d")}')
            except ValueError:
                # 잘못된 날짜 형식은 "조용한 실패" 대신 "명시적 오류"를 반환
                return {"status": STATUS_ERROR, "error": ERROR_INVALID_DATE_FORMAT.format(date_on, "날짜 형식이 올바르지 않습니다")}
        elif date_after and date_before:
            query_parts.append(f'after:{date_after} before:{date_before}')
        elif date_after:
            query_parts.append(f'after:{date_after}')
        elif date_before:
            query_parts.append(f'before:{date_before}')
        
        # 모든 검색 조건을 하나의 문자열로 합침
        query_content = ' '.join(query_parts)
        
        # 디버깅을 위해 로깅
        logger.debug(f"Sending query content: {query_content}")

        # 한글 등 비 ASCII 문자가 포함된 검색어를 서버에 안전하게 전달하기 위해
        # 쿼리 내용을 UTF-8로 인코딩하여 imaplib에 직접 전달
        status, messages = mail.uid('search', 'CHARSET', 'UTF-8', 'X-GM-RAW', query_content.encode('utf-8'))

        if status != 'OK':
            # 실패 시 서버 응답을 함께 보여주어 디버깅을 돕습니다
            return {"status": STATUS_ERROR, "error": ERROR_SEARCH_FAILED.format(status, messages)}

        email_ids = messages[0].split()
        if not email_ids:
            return {"status": STATUS_SUCCESS, "message": SUCCESS_NO_EMAILS_FOUND, "emails": []}

        # 가장 최근 이메일부터 가져오기
        email_ids = email_ids[::-1][:max_results]
        
        results = []
        for email_id in email_ids:
            # mail.uid('search',...)로 UID를 받았으므로, fetch도 UID로 해야 함
            status, msg_data = mail.uid('fetch', email_id, '(RFC822)')
            if status == 'OK':
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        results.append({
                            "message_id": email_id.decode(),
                            "from": clean_header(msg['From']),
                            "to": clean_header(msg['To']),
                            "subject": clean_header(msg['Subject']),
                            "date": msg['Date']
                        })
        mail.logout()
        return {"status": STATUS_SUCCESS, "emails": results}

    except Exception as e:
        error_msg = f"An error occurred while searching emails: {str(e)}"
        logger.error(error_msg)
        logger.debug(traceback.format_exc())
        return {"status": STATUS_ERROR, "error": error_msg}


def get_email_details(email_id: str, mail_folder: str = DEFAULT_MAIL_FOLDER) -> Dict[str, Any]:
    """
    특정 이메일의 상세 내용을 가져옵니다.
    
    Args:
        email_id (str): 가져올 이메일의 ID
        mail_folder (str): 검색할 메일 폴더, 기본값은 'inbox'
        
    Returns:
        Dict[str, Any]: 이메일 상세 정보를 포함하는 딕셔너리
    """
    try:
        # 인증 정보 확인
        try:
            _, _ = get_credentials()
        except ValueError:
            return {"status": STATUS_ERROR, "error": ERROR_CREDENTIALS_NOT_CONFIGURED}
        
        # IMAP 연결
        mail = get_imap_connection()
        mail.select(mail_folder)

        # 이메일 가져오기
        status, msg_data = mail.fetch(email_id, '(RFC822)')
        if status != 'OK':
            return {"status": STATUS_ERROR, "error": ERROR_FETCH_EMAIL.format(status)}

        # 이메일 데이터 추출
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                return {
                    "status": STATUS_SUCCESS,
                    "message_id": email_id,
                    "from": clean_header(msg['From']),
                    "to": clean_header(msg['To']),
                    "subject": clean_header(msg['Subject']),
                    "date": msg['Date'],
                    "body": get_email_body(msg)
                }
        mail.logout()
        return {"status": STATUS_ERROR, "error": ERROR_EMAIL_NOT_FOUND}
    except Exception as e:
        error_msg = f"An error occurred while fetching email details: {str(e)}"
        logger.error(error_msg)
        logger.debug(traceback.format_exc())
        return {"status": STATUS_ERROR, "error": error_msg}


def send_reply(email_id: str, reply_body: str, mail_folder: str = DEFAULT_MAIL_FOLDER) -> Dict[str, Any]:
    """
    특정 이메일에 대한 답장을 보냅니다.
    
    Args:
        email_id (str): 답장을 보낼 이메일의 ID
        reply_body (str): 답장 내용
        mail_folder (str): 검색할 메일 폴더, 기본값은 'inbox'
        
    Returns:
        Dict[str, Any]: 답장 전송 결과를 포함하는 딕셔너리
    """
    try:
        # 인증 정보 확인
        try:
            gmail_address, _ = get_credentials()
        except ValueError:
            return {"status": STATUS_ERROR, "error": ERROR_CREDENTIALS_NOT_CONFIGURED}
        
        # IMAP 연결
        mail = get_imap_connection()
        mail.select(mail_folder)

        # 원본 이메일 가져오기
        status, msg_data = mail.fetch(email_id, '(RFC822)')
        if status != 'OK':
            return {"status": STATUS_ERROR, "error": ERROR_FETCH_EMAIL.format(status)}

        # 답장 작성 및 전송
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                from_addr = clean_header(msg['From'])
                subject = clean_header(msg['Subject'])

                # 답장 메시지 작성
                reply_msg = MIMEMultipart()
                reply_msg['From'] = gmail_address
                reply_msg['To'] = from_addr
                reply_msg['Subject'] = f"Re: {subject}"
                reply_msg.attach(MIMEText(reply_body, 'plain'))

                # 답장 이메일 전송
                smtp = get_smtp_connection()
                smtp.sendmail(gmail_address, from_addr, reply_msg.as_string())
                smtp.quit()

                return {"status": STATUS_SUCCESS, "message": SUCCESS_REPLY_SENT}
        mail.logout()
        return {"status": STATUS_ERROR, "error": ERROR_EMAIL_NOT_FOUND}
    except Exception as e:
        error_msg = f"An error occurred while sending reply: {str(e)}"
        logger.error(error_msg)
        logger.debug(traceback.format_exc())
        return {"status": STATUS_ERROR, "error": error_msg}


def save_attachments(email_id: str, save_path: str, mail_folder: str = DEFAULT_MAIL_FOLDER) -> Dict[str, Any]:
    """
    특정 이메일의 첨부 파일을 로컬 경로에 저장합니다.
    
    Args:
        email_id (str): 첨부 파일을 저장할 이메일의 ID
        save_path (str): 첨부 파일을 저장할 경로
        mail_folder (str): 검색할 메일 폴더, 기본값은 'inbox'
        
    Returns:
        Dict[str, Any]: 첨부 파일 저장 결과를 포함하는 딕셔너리
    """
    try:
        # 인증 정보 확인
        try:
            _, _ = get_credentials()
        except ValueError:
            return {"status": STATUS_ERROR, "error": ERROR_CREDENTIALS_NOT_CONFIGURED}
        
        # IMAP 연결
        mail = get_imap_connection()
        mail.select(mail_folder)

        # 이메일 가져오기
        status, msg_data = mail.fetch(email_id, '(RFC822)')
        if status != 'OK':
            return {"status": STATUS_ERROR, "error": ERROR_FETCH_EMAIL.format(status)}

        saved_files = []
        # 첨부 파일 처리
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                for part in msg.walk():
                    if part.get_content_maintype() == 'multipart':
                        continue
                    if part.get('Content-Disposition') is None:
                        continue

                    filename = part.get_filename()
                    if filename:
                        filepath = os.path.join(save_path, filename)
                        with open(filepath, 'wb') as f:
                            f.write(part.get_payload(decode=True))
                        saved_files.append(filepath)
        mail.logout()
        if saved_files:
            return {"status": STATUS_SUCCESS, "message": SUCCESS_ATTACHMENT_SAVED.format(', '.join(saved_files)), "saved_files": saved_files}
        else:
            return {"status": STATUS_ERROR, "error": ERROR_NO_ATTACHMENTS}
    except Exception as e:
        error_msg = f"An error occurred while saving attachments: {str(e)}"
        logger.error(error_msg)
        logger.debug(traceback.format_exc())
        return {"status": STATUS_ERROR, "error": error_msg}


def get_daily_email_summary(days_ago: int = 0, mail_folder: str = "inbox", max_results: int = 20) -> Dict[str, Any]:
    """
    특정 날짜에 수신된 이메일의 요약을 가져옵니다.
    
    Args:
        days_ago (int): 오늘로부터 며칠 전의 이메일을 검색할지 지정, 기본값은 0(오늘)
        mail_folder (str): 검색할 메일 폴더, 기본값은 'inbox'
        max_results (int): 최대 결과 수, 기본값은 20
        
    Returns:
        Dict[str, Any]: 이메일 요약 정보를 포함하는 딕셔너리
    """
    try:
        # days_ago 유효성 검사
        if days_ago < 0:
            return {"status": STATUS_ERROR, "error": "days_ago must be a non-negative integer"}
        
        # 인증 정보 확인
        try:
            _, _ = get_credentials()
        except ValueError:
            return {"status": STATUS_ERROR, "error": ERROR_CREDENTIALS_NOT_CONFIGURED}
        
        # IMAP 연결
        mail = get_imap_connection()
        mail.select(mail_folder)

        # 검색할 날짜 계산
        target_date = datetime.now() - timedelta(days=days_ago)
        date_str = target_date.strftime("%d-%b-%Y")

        # 특정 날짜의 이메일 검색
        search_query = f'(ON {date_str})'
        status, data = mail.search(None, search_query)
        if status != 'OK':
            return {"status": STATUS_ERROR, "error": ERROR_SEARCH_FAILED.format(status, data)}

        email_ids = data[0].split()
        if not email_ids:
            return {"status": STATUS_SUCCESS, "message": f"No emails found on {date_str}", "emails": []}

        # 결과 수 제한
        email_ids = email_ids[-max_results:] if len(email_ids) > max_results else email_ids

        emails = []
        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            if status != 'OK':
                continue

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    emails.append({
                        "message_id": email_id.decode(),
                        "from": clean_header(msg['From']),
                        "subject": clean_header(msg['Subject']),
                        "date": msg['Date']
                    })
                    break

        mail.logout()
        return {
            "status": STATUS_SUCCESS, 
            "message": f"Found {len(emails)} emails on {date_str}", 
            "emails": emails
        }
    except Exception as e:
        error_msg = f"An error occurred while getting daily email summary: {str(e)}"
        logger.error(error_msg)
        logger.debug(traceback.format_exc())
        return {"status": STATUS_ERROR, "error": error_msg}

def send_email(
    to: str,
    subject: str,
    body: str,
    body_type: str = "plain",
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    attachments: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    임의의 수신자에게 새 이메일을 보냅니다.
    Args:
        to (str): 수신자 이메일 주소(여러 명은 콤마로 구분)
        subject (str): 이메일 제목
        body (str): 이메일 본문
        body_type (str): 본문 타입("plain" 또는 "html"), 기본값은 plain
        cc (Optional[str]): 참조(여러 명은 콤마)
        bcc (Optional[str]): 숨은참조(여러 명은 콤마)
        attachments (Optional[List[str]]): 첨부파일 경로 리스트
    Returns:
        Dict[str, Any]: 발송 결과
    """
    try:
        gmail_address, _ = get_credentials()
        msg = MIMEMultipart()
        msg['From'] = gmail_address
        msg['To'] = to
        msg['Subject'] = subject
        if cc:
            msg['Cc'] = cc
        if bcc:
            msg['Bcc'] = bcc
        msg.attach(MIMEText(body, body_type))
        # 첨부파일 처리
        if attachments:
            from email.mime.base import MIMEBase
            from email import encoders
            for file_path in attachments:
                try:
                    with open(file_path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(file_path)}"')
                    msg.attach(part)
                except Exception as e:
                    logger.warning(f"첨부파일 추가 실패: {file_path}, {e}")
        smtp = get_smtp_connection()
        recipients = [x.strip() for x in to.split(',')]
        if cc:
            recipients += [x.strip() for x in cc.split(',')]
        if bcc:
            recipients += [x.strip() for x in bcc.split(',')]
        smtp.sendmail(gmail_address, recipients, msg.as_string())
        smtp.quit()
        return {"status": STATUS_SUCCESS, "message": "Email sent successfully."}
    except Exception as e:
        logger.error(f"메일 발송 실패: {e}")
        logger.debug(traceback.format_exc())
        return {"status": STATUS_ERROR, "error": str(e)}

# --- Tool Schemas and Function Map for the Assistant ---
# Schema for the search_emails function
search_emails_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_emails",
        "description": "Searches a user's Gmail account with advanced criteria. Can filter by keywords, subject, and date ranges (on, after, before). Fully supports Korean and other UTF-8 characters.",
        "parameters": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "A list of keywords to search for in the email body or subject."
                },
                "subject": {
                    "type": "string",
                    "description": "Keywords to search for specifically in the email's subject line."
                },
                "date_on": {
                    "type": "string",
                    "description": "The specific date to search for emails (e.g., 'YYYY/MM/DD')."
                },
                "date_after": {
                    "type": "string",
                    "description": "The start date for a search range (e.g., 'YYYY/MM/DD'). Use with date_before."
                },
                "date_before": {
                    "type": "string",
                    "description": "The end date for a search range (e.g., 'YYYY/MM/DD'). Use with date_after."
                },
                "mail_folder": {
                    "type": "string",
                    "description": f"The mail folder to search in. Defaults to '{DEFAULT_MAIL_FOLDER}'.",
                    "default": DEFAULT_MAIL_FOLDER
                },
                "max_results": {
                    "type": "integer",
                    "description": f"The maximum number of emails to return. Defaults to {DEFAULT_MAX_RESULTS}.",
                    "default": DEFAULT_MAX_RESULTS
                }
            },
            "required": []
        }
    }
}

# Schema for the get_email_details function
get_email_details_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_email_details",
        "description": "Fetches the details of a specific email.",
        "parameters": {
            "type": "object",
            "properties": {
                "email_id": {
                    "type": "string",
                    "description": "The ID of the email to fetch."
                },
                "mail_folder": {
                    "type": "string",
                    "description": f"The mail folder to search in. Defaults to '{DEFAULT_MAIL_FOLDER}'.",
                    "default": DEFAULT_MAIL_FOLDER
                }
            },
            "required": ["email_id"]
        }
    }
}

# Schema for the send_reply function
send_reply_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "send_reply",
        "description": "Sends a reply to a specific email.",
        "parameters": {
            "type": "object",
            "properties": {
                "email_id": {
                    "type": "string",
                    "description": "The ID of the email to reply to."
                },
                "reply_body": {
                    "type": "string",
                    "description": "The body of the reply email."
                },
                "mail_folder": {
                    "type": "string",
                    "description": f"The mail folder to search in. Defaults to '{DEFAULT_MAIL_FOLDER}'.",
                    "default": DEFAULT_MAIL_FOLDER
                }
            },
            "required": ["email_id", "reply_body"]
        }
    }
}

# Schema for the save_attachments function
save_attachments_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "save_attachments",
        "description": "Saves the attachments of a specific email.",
        "parameters": {
            "type": "object",
            "properties": {
                "email_id": {
                    "type": "string",
                    "description": "The ID of the email to save attachments from."
                },
                "save_path": {
                    "type": "string",
                    "description": "The path to save the attachments."
                },
                "mail_folder": {
                    "type": "string",
                    "description": f"The mail folder to search in. Defaults to '{DEFAULT_MAIL_FOLDER}'.",
                    "default": DEFAULT_MAIL_FOLDER
                }
            },
            "required": ["email_id", "save_path"]
        }
    }
}

# Schema for the get_daily_email_summary function
get_daily_email_summary_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_daily_email_summary",
        "description": "Fetches a summary of emails from a specific day.",
        "parameters": {
            "type": "object",
            "properties": {
                "days_ago": {
                    "type": "integer",
                    "description": "How many days back to search (0 for today, 1 for yesterday, etc.). Defaults to 0.",
                    "default": 0
                },
                "mail_folder": {
                    "type": "string",
                    "description": f"The mail folder to search in. Defaults to '{DEFAULT_MAIL_FOLDER}'.",
                    "default": DEFAULT_MAIL_FOLDER
                },
                "max_results": {
                    "type": "integer",
                    "description": f"The maximum number of emails to return. Defaults to {DEFAULT_MAX_RESULTS}.",
                    "default": DEFAULT_MAX_RESULTS
                }
            },
            "required": []
        }
    }
}

# Schema for the send_email function
send_email_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "send_email",
        "description": "임의의 수신자에게 새 이메일을 보냅니다. 참조/숨은참조/첨부파일도 지원.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "수신자 이메일 주소(여러 명은 콤마로 구분)"},
                "subject": {"type": "string", "description": "이메일 제목"},
                "body": {"type": "string", "description": "이메일 본문 내용"},
                "body_type": {"type": "string", "description": "본문 타입(plain 또는 html)", "default": "plain", "enum": ["plain", "html"]},
                "cc": {"type": "string", "description": "참조(여러 명은 콤마)", "default": ""},
                "bcc": {"type": "string", "description": "숨은참조(여러 명은 콤마)", "default": ""},
                "attachments": {"type": "array", "items": {"type": "string"}, "description": "첨부파일 경로 리스트", "default": []}
            },
            "required": ["to", "subject", "body"]
        }
    }
}

# The list of all tool schemas for the assistant to use
TOOL_SCHEMAS = [search_emails_TOOL_SCHEMA, get_email_details_TOOL_SCHEMA, send_reply_TOOL_SCHEMA, save_attachments_TOOL_SCHEMA, get_daily_email_summary_TOOL_SCHEMA, send_email_TOOL_SCHEMA]

# The map of function names to their actual Python functions
TOOL_MAP = {
    "search_emails": search_emails,
    "get_email_details": get_email_details,
    "send_reply": send_reply,
    "save_attachments": save_attachments,
    "get_daily_email_summary": get_daily_email_summary,
    "send_email": send_email,
}

def validate_tool_interface() -> None:
    """
    TOOL_SCHEMAS와 TOOL_MAP이 일치하는지 검증하는 함수
    
    Raises:
        ValueError: 스키마와 함수 맵이 일치하지 않을 경우 발생
    """
    # 스키마에 정의된 모든 함수가 TOOL_MAP에 존재하는지 확인
    schema_function_names = [schema["function"]["name"] for schema in TOOL_SCHEMAS]
    for name in schema_function_names:
        if name not in TOOL_MAP:
            logger.error(f"스키마에 정의된 함수 '{name}'이 TOOL_MAP에 존재하지 않습니다.")
            raise ValueError(f"스키마에 정의된 함수 '{name}'이 TOOL_MAP에 존재하지 않습니다.")
    
    # TOOL_MAP의 모든 함수가 스키마에 정의되어 있는지 확인
    for name in TOOL_MAP:
        if name not in schema_function_names:
            logger.error(f"TOOL_MAP에 정의된 함수 '{name}'이 스키마에 존재하지 않습니다.")
            raise ValueError(f"TOOL_MAP에 정의된 함수 '{name}'이 스키마에 존재하지 않습니다.")
    
    # TOOL_MAP의 모든 함수가 호출 가능한지 확인
    for name, func in TOOL_MAP.items():
        if not callable(func):
            logger.error(f"TOOL_MAP의 '{name}'에 매핑된 객체가 호출 가능한 함수가 아닙니다.")
            raise ValueError(f"TOOL_MAP의 '{name}'에 매핑된 객체가 호출 가능한 함수가 아닙니다.")
    
    logger.info("email_tool 모듈이 표준 인터페이스를 준수합니다.")

# 모듈이 로드될 때 자동으로 검증 실행
validate_tool_interface()