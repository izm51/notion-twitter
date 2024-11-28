import os
import requests
import pydantic
import datetime
import random
from notion2md.exporter.block import StringExporter


class NotionData(pydantic.BaseModel):
    id: str
    title: str
    created_time: datetime.datetime


class NotionHandler:
    def __init__(self):
        self.api_key = os.environ["NOTION_API_KEY"]
        self.database_id = "decb8944082e473793322534544f4fcf"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

    def fetch_notion_data(self):
        start_iso = (
            datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=365)
        ).isoformat()

        payload = {
            "filter": {
                "and": [
                    {
                        "property": "サマリ不要",
                        "checkbox": {"equals": False},
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
            created_time = datetime.datetime.fromisoformat(
                page["created_time"].replace("Z", "+00:00")
            )
            notion_data = NotionData(id=id, title=title, created_time=created_time)
            notion_data_list.append(notion_data)
        return notion_data_list

    def select_notion_data(self, notion_data_list: list[NotionData]) -> NotionData:
        now = datetime.datetime.now(datetime.timezone.utc)
        yesterday = now - datetime.timedelta(days=1)
        week_ago = now - datetime.timedelta(days=7)

        yesterday_data = []
        week_data = []
        month_data = []

        for data in notion_data_list:
            if data.created_time >= yesterday:
                yesterday_data.append(data)
            elif data.created_time >= week_ago:
                week_data.append(data)
            else:
                month_data.append(data)

        period_weights = [0.6, 0.2, 0.2]
        period_data = [yesterday_data, week_data, month_data]

        valid_periods = [
            (data, weight) for data, weight in zip(period_data, period_weights) if data
        ]
        if not valid_periods:
            raise ValueError("No valid data found in the specified time periods")

        selected_period_data, _ = random.choices(
            valid_periods, weights=[w for _, w in valid_periods], k=1
        )[0]

        return random.choice(selected_period_data)

    def get_page_content(self, page_id: str) -> str:
        os.environ["NOTION_TOKEN"] = self.api_key
        return StringExporter(block_id=page_id).export()
