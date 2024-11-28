import os
import requests
import pydantic
from datetime import datetime, timezone, timedelta
import random
from notion2md.exporter.block import StringExporter


class NotionData(pydantic.BaseModel):
    id: str
    title: str
    created_time: datetime


class NotionConfig:
    API_VERSION = "2022-06-28"
    DATABASE_ID = "decb8944082e473793322534544f4fcf"
    DAYS_LOOKBACK = 365

    # 重み付けの設定
    WEIGHT_YESTERDAY = 0.6
    WEIGHT_WEEK = 0.2
    WEIGHT_OLDER = 0.2


class NotionHandler:
    def __init__(self):
        self.api_key = os.environ["NOTION_API_KEY"]
        self.database_id = NotionConfig.DATABASE_ID
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": NotionConfig.API_VERSION,
            "Content-Type": "application/json",
        }

    def fetch_notion_data(self):
        start_iso = (
            datetime.now(timezone.utc) - timedelta(days=NotionConfig.DAYS_LOOKBACK)
        ).isoformat()

        payload = {
            "filter": {
                "and": [
                    {
                        "property": "サマリ対象",
                        "checkbox": {"equals": True},
                    },
                    {
                        "timestamp": "created_time",
                        "created_time": {"on_or_after": start_iso},
                    },
                ],
            },
            "sorts": [{"property": "作成日時", "direction": "ascending"}],
        }

        url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        response = requests.post(url, headers=self.headers, json=payload)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"status_code: {response.status_code}, message: {response.text}"
            )

    def convert_to_notion_data(self, data: dict) -> list[NotionData]:
        notion_data_list = []
        for page in data["results"]:
            id = page["id"]
            title = page["properties"]["名前"]["title"][0]["text"]["content"]
            created_time = datetime.fromisoformat(
                page["created_time"].replace("Z", "+00:00")
            )
            notion_data = NotionData(id=id, title=title, created_time=created_time)
            notion_data_list.append(notion_data)
        return notion_data_list

    def _calculate_weight(self, data: NotionData) -> float:
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)

        if data.created_time >= yesterday:
            return NotionConfig.WEIGHT_YESTERDAY
        elif data.created_time >= week_ago:
            return NotionConfig.WEIGHT_WEEK
        return NotionConfig.WEIGHT_OLDER

    def select_notion_data(self, notion_data_list: list[NotionData]) -> NotionData:
        weights = [self._calculate_weight(data) for data in notion_data_list]
        return random.choices(notion_data_list, weights=weights, k=1)[0]

    def get_page_content(self, page_id: str) -> str:
        os.environ["NOTION_TOKEN"] = self.api_key
        return StringExporter(block_id=page_id).export()
