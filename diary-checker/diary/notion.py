from datetime import date
from notion_client import Client

TEXT_BLOCK_TYPES = {
    "paragraph",
    "heading_1",
    "heading_2",
    "heading_3",
    "bulleted_list_item",
    "numbered_list_item",
    "quote",
    "callout",
}


class NotionDiaryClient:
    def __init__(self, client: Client, parent_id: str):
        self._client = client
        self._parent_id = parent_id

    def get_today_page_id(self) -> str | None:
        """오늘 날짜(YYYYMMDD)로 시작하는 하위 페이지 ID를 반환한다."""
        today_prefix = date.today().strftime("%Y%m%d")
        cursor = None

        while True:
            kwargs = {"block_id": self._parent_id, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor

            response = self._client.blocks.children.list(**kwargs)

            for block in response["results"]:
                if block.get("type") == "child_page" and not block.get("in_trash"):
                    title = block["child_page"]["title"]
                    if title.startswith(today_prefix):
                        return block["id"]

            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

        return None

    def extract_text(self, page_id: str) -> str:
        """페이지의 모든 텍스트 블록을 추출하여 하나의 문자열로 반환한다.

        has_children=True인 블록(toggle, callout, quote 등)은 재귀적으로 하위 블록을 탐색한다.
        """
        lines: list[str] = []
        cursor = None

        while True:
            kwargs = {"block_id": page_id, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor

            response = self._client.blocks.children.list(**kwargs)

            for block in response["results"]:
                block_type = block.get("type")
                if block_type in TEXT_BLOCK_TYPES:
                    rich_text = block[block_type].get("rich_text", [])
                    text = "".join(rt.get("plain_text", "") for rt in rich_text)
                    if text:
                        lines.append(text)

                # 하위 블록이 있으면 재귀 탐색 (텍스트 추출 여부와 무관하게 수행)
                if block.get("has_children"):
                    child_text = self.extract_text(block["id"])
                    if child_text:
                        lines.append(child_text)

            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

        return "\n".join(lines)


def make_client(token: str, parent_id: str) -> NotionDiaryClient:
    """환경변수로 초기화된 NotionDiaryClient를 반환한다."""
    return NotionDiaryClient(client=Client(auth=token), parent_id=parent_id)
