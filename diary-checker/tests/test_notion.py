from unittest.mock import MagicMock
from datetime import date
from diary.notion import NotionDiaryClient


PARENT_ID = "2dbad192-0f86-80b7-bb55-e9614da3413a"


def make_child_page_block(title: str, block_id: str) -> dict:
    return {
        "object": "block",
        "id": block_id,
        "type": "child_page",
        "child_page": {"title": title},
        "has_children": True,
        "in_trash": False,
    }


def test_get_today_page_id_found():
    """오늘 날짜로 시작하는 페이지 ID를 반환한다"""
    today = date.today().strftime("%Y%m%d")
    mock_client = MagicMock()
    mock_client.blocks.children.list.return_value = {
        "results": [make_child_page_block(f"{today}_테스트", "page-id-123")],
        "has_more": False,
        "next_cursor": None,
    }
    diary = NotionDiaryClient(client=mock_client, parent_id=PARENT_ID)
    assert diary.get_today_page_id() == "page-id-123"


def test_get_today_page_id_not_found():
    """오늘 날짜 페이지가 없으면 None 반환"""
    mock_client = MagicMock()
    mock_client.blocks.children.list.return_value = {
        "results": [make_child_page_block("20260101_과거", "old-page")],
        "has_more": False,
        "next_cursor": None,
    }
    diary = NotionDiaryClient(client=mock_client, parent_id=PARENT_ID)
    assert diary.get_today_page_id() is None


def test_get_today_page_id_pagination():
    """has_more=True일 때 페이지네이션으로 계속 탐색한다"""
    today = date.today().strftime("%Y%m%d")
    mock_client = MagicMock()
    mock_client.blocks.children.list.side_effect = [
        {
            "results": [make_child_page_block("20260101", "old-1")],
            "has_more": True,
            "next_cursor": "cursor-abc",
        },
        {
            "results": [make_child_page_block(today, "today-page")],
            "has_more": False,
            "next_cursor": None,
        },
    ]
    diary = NotionDiaryClient(client=mock_client, parent_id=PARENT_ID)
    assert diary.get_today_page_id() == "today-page"
    assert mock_client.blocks.children.list.call_count == 2


def test_extract_text_paragraph():
    """paragraph 블록에서 텍스트를 추출한다"""
    mock_client = MagicMock()
    mock_client.blocks.children.list.return_value = {
        "results": [
            {
                "type": "paragraph",
                "paragraph": {"rich_text": [{"plain_text": "오늘은 맑은 날이었다."}]},
                "has_children": False,
            }
        ],
        "has_more": False,
    }
    diary = NotionDiaryClient(client=mock_client, parent_id=PARENT_ID)
    assert "오늘은 맑은 날이었다." in diary.extract_text("some-page-id")


def test_extract_text_multiple_block_types():
    """heading, paragraph, bulleted_list_item 등 여러 타입을 처리한다"""
    mock_client = MagicMock()
    mock_client.blocks.children.list.return_value = {
        "results": [
            {"type": "heading_1", "heading_1": {"rich_text": [{"plain_text": "제목"}]}, "has_children": False},
            {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "본문"}]}, "has_children": False},
            {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"plain_text": "목록"}]}, "has_children": False},
        ],
        "has_more": False,
    }
    diary = NotionDiaryClient(client=mock_client, parent_id=PARENT_ID)
    text = diary.extract_text("some-page-id")
    assert "제목" in text
    assert "본문" in text
    assert "목록" in text


def test_extract_text_empty_page():
    """내용 없는 페이지는 빈 문자열을 반환한다"""
    mock_client = MagicMock()
    mock_client.blocks.children.list.return_value = {"results": [], "has_more": False}
    diary = NotionDiaryClient(client=mock_client, parent_id=PARENT_ID)
    assert diary.extract_text("empty-page-id") == ""


def test_extract_text_pagination():
    """has_more=True일 때 페이지네이션으로 모든 블록을 추출한다"""
    mock_client = MagicMock()
    mock_client.blocks.children.list.side_effect = [
        {
            "results": [
                {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "첫 번째 페이지 내용"}]}, "has_children": False}
            ],
            "has_more": True,
            "next_cursor": "cursor-xyz",
        },
        {
            "results": [
                {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "두 번째 페이지 내용"}]}, "has_children": False}
            ],
            "has_more": False,
        },
    ]
    diary = NotionDiaryClient(client=mock_client, parent_id=PARENT_ID)
    text = diary.extract_text("long-page-id")
    assert "첫 번째 페이지 내용" in text
    assert "두 번째 페이지 내용" in text
    assert mock_client.blocks.children.list.call_count == 2
