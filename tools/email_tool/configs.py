# tools/email_tool/configs.py
"""
이메일 도구에서 사용하는 설정 및 상수를 정의하는 모듈입니다.
"""

import os

# --- IMAP/SMTP Server Settings ---
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# --- Default Values ---
DEFAULT_MAIL_FOLDER = "inbox"
DEFAULT_MAX_RESULTS = 10

# --- Response Status Codes ---
STATUS_SUCCESS = "success"
STATUS_ERROR = "error"
STATUS_INFO = "info"

# --- Error Messages ---
ERROR_CREDENTIALS_NOT_CONFIGURED = "Gmail credentials are not configured in the .env file."
ERROR_EMPTY_SEARCH_QUERY = "Search query is empty. Please provide keywords or a subject."
ERROR_FETCH_EMAIL = "Failed to fetch email: {}"
ERROR_EMAIL_NOT_FOUND = "Email not found."
ERROR_NO_ATTACHMENTS = "No attachments found."
ERROR_SEARCH_FAILED = "Failed to search emails. Status: {}, Response: {}"
ERROR_INVALID_DATE_FORMAT = "Invalid date format for '{}': {}. Please use YYYY-MM-DD or YYYY/MM/DD."

# --- Success Messages ---
SUCCESS_REPLY_SENT = "Reply sent successfully."
SUCCESS_ATTACHMENT_SAVED = "Attachment saved to {}"
SUCCESS_NO_EMAILS_FOUND = "No emails found with the specified criteria."
SUCCESS_NO_EMAILS_ON_DATE = "No emails found on {}."
