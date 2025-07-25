# tools/notion_utils.py

import os
import requests
import json # JSON 파싱을 위해 추가
from dotenv import load_dotenv

# .env 파일 로드 (공용 유틸리티에서도 환경 변수를 직접 사용)
load_dotenv(override=True)

# Notion API 키와 부모 페이지 ID를 환경 변수에서 로드
NOTION_API_KEY = os.environ.get("NOTION_API_KEY") # .env 파일에서 "NOTION_API_KEY"로 설정된 값
NOTION_PARENT_PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID") # .env 파일에서 "NOTION_PARENT_PAGE_ID"로 설정된 값

def search_notion_pages_by_keyword(keyword: str, page_size: int = 20) -> list:
    """
    Notion에서 특정 키워드로 페이지를 검색하고, 제목, ID, 마지막 수정 시간을 반환합니다.
    Args:
        keyword (str): 검색할 키워드.
        page_size (int): 가져올 최대 페이지 수.
    Returns:
        list: 각 페이지의 'id', 'title', 'last_edited_time'을 포함하는 딕셔너리 리스트.
    """
    if not NOTION_API_KEY:
        print("ERROR: Notion API Key is not set for search_notion_pages_by_keyword. Check .env file.")
        return []

    url = "https://api.notion.com/v1/search"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28", # Notion API 버전
        "Content-Type": "application/json"
    }
    data = {
        "query": keyword,
        "page_size": page_size,
        "sort": {"direction": "descending", "timestamp": "last_edited_time"}
    }
    
    try:
        res = requests.post(url, headers=headers, json=data)
        res.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        results = res.json().get("results", [])
        
        docs = []
        for page in results:
            if page.get("object") == "page":
                props = page.get("properties", {})
                title = None
                # Notion API 응답에서 제목을 추출하는 로직 (타이틀 속성은 다양한 형태로 올 수 있음)
                for k in props:
                    if props[k].get("type") == "title":
                        texts = props[k].get("title", [])
                        if texts and isinstance(texts, list) and "plain_text" in texts[0]:
                            title = texts[0]["plain_text"]
                            break # 첫 번째 타이틀 속성만 사용
                
                if not title:
                    # 제목이 없는 페이지는 건너뜀
                    continue
                
                docs.append({
                    "id": page["id"],
                    "title": title,
                    "last_edited_time": page.get("last_edited_time", "")[:19].replace("T", " "),
                })
        return docs
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Notion search request failed: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to decode Notion search response JSON: {e}")
        return []
    except Exception as e:
        print(f"ERROR: An unexpected error occurred during Notion search: {e}")
        return []


def get_page_content(page_id: str) -> str:
    """
    Notion 페이지 ID를 받아 페이지의 모든 블록 내용을 텍스트로 가져옵니다.
    Args:
        page_id (str): Notion 페이지의 ID.
    Returns:
        str: 페이지의 모든 블록 내용을 합친 텍스트.
    """
    if not NOTION_API_KEY:
        print("ERROR: Notion API Key is not set for get_page_content. Check .env file.")
        return ""

    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        blocks = res.json().get("results", [])
        
        texts = []
        for block in blocks:
            t = ""
            # 다양한 블록 타입에서 rich_text 또는 text 내용을 추출
            if block.get("type") in [
                "paragraph", "heading_1", "heading_2", "heading_3",
                "bulleted_list_item", "numbered_list_item", "to_do", "toggle",
                "code", "quote" # 코드 블록이나 인용 블록도 포함
            ]:
                # rich_text가 있으면 rich_text, 아니면 text (legacy)
                content_field = block[block["type"]].get("rich_text") or block[block["type"]].get("text")
                if content_field:
                    for t_obj in content_field:
                        t += t_obj.get("plain_text", "")
            elif block.get("type") == "child_page":
                # 자식 페이지는 제목만 가져옴
                t = block["child_page"].get("title", "")
            
            if t:
                texts.append(t)
        return "\n".join(texts)
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Notion get_page_content request failed: {e}")
        return ""
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to decode Notion get_page_content response JSON: {e}")
        return ""
    except Exception as e:
        print(f"ERROR: An unexpected error occurred during getting Notion page content: {e}")
        return ""


def upload_to_notion(title: str, content: str) -> tuple:
    """
    제목과 내용을 받아 Notion에 새 페이지로 업로드합니다.
    Args:
        title (str): Notion 페이지의 제목.
        content (str): Notion 페이지에 들어갈 내용.
    Returns:
        tuple: (bool 성공여부, str 결과_메시지_또는_URL)
    """
    if not NOTION_API_KEY or not NOTION_PARENT_PAGE_ID:
        print("ERROR: Notion API Key 또는 Parent Page ID가 설정되지 않았습니다. Check .env file.")
        return False, "Notion API Key 또는 Parent Page ID가 설정되지 않았습니다."
        
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28", # Notion API 버전 (requests.post의 'Content-Version'은 Notion API 헤더가 아님)
        "Content-Type": "application/json"
    }
    
    # Notion API 텍스트 블록은 최대 2000자이므로, 긴 문서의 경우 잘릴 수 있습니다.
    # 더 긴 문서를 처리하려면 여러 블록으로 분할하여 업로드하는 로직이 필요합니다.
    data = {
        "parent": {"page_id": NOTION_PARENT_PAGE_ID},
        "properties": {
            "title": {
                "title": [
                    {"text": {"content": title}}
                ]
            }
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": { "content": content[:1999] } # Notion API 텍스트 블록 한계 고려 (2000자)
                        }
                    ]
                }
            }
        ]
    }
    
    try:
        res = requests.post(url, headers=headers, json=data)
        res.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        page_url = res.json().get("url", "")
        return True, page_url
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Notion API Upload request failed: {res.status_code} - {res.text} - {e}")
        return False, f"Notion API Upload failed: {res.status_code} - {res.text}"
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to decode Notion upload response JSON: {e}")
        return False, f"Failed to decode Notion upload response: {e}"
    except Exception as e:
        print(f"ERROR: An unexpected error occurred during Notion upload: {e}")
        return False, f"An unexpected error occurred during Notion upload: {e}"