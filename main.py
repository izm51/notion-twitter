import os
import requests
import pydantic
import datetime
import random


def fetch_notion_data():
    NOTION_API_KEY = os.environ["NOTION_API_KEY"]
    DATABASE_ID = "decb8944082e473793322534544f4fcf"

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    start_iso = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
    ).isoformat()

    payload = {
        "filter": {
            "and": [
                {
                    "timestamp": "created_time",
                    "created_time": {"on_or_after": start_iso},
                },
            ],
        },
        "sorts": [{"property": "作成日時", "direction": "ascending"}],
    }

    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    response = requests.post(url, headers=headers, json=payload)

    # レスポンスの確認
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        raise Exception(
            f"status_code: {response.status_code}, message: {response.text}"
        )


class NotionData(pydantic.BaseModel):
    id: str
    title: str
    created_time: datetime.datetime


def convert_to_notion_data(data: dict) -> list[NotionData]:
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


def select_notion_data(notion_data_list: list[NotionData]) -> NotionData:
    # 現在時刻を取得
    now = datetime.datetime.now(datetime.timezone.utc)
    yesterday = now - datetime.timedelta(days=1)
    week_ago = now - datetime.timedelta(days=7)
    month_ago = now - datetime.timedelta(days=30)

    # 期間ごとにデータを振り分け
    yesterday_data = []
    week_data = []
    month_data = []

    for data in notion_data_list:
        if data.created_time >= yesterday:
            yesterday_data.append(data)
        elif data.created_time >= week_ago:
            week_data.append(data)
        elif data.created_time >= month_ago:
            month_data.append(data)

    # 確率に基づいて期間を選択
    period_weights = [0.6, 0.2, 0.2]
    period_data = [yesterday_data, week_data, month_data]

    # 空でない期間のみを対象にする
    valid_periods = [
        (data, weight) for data, weight in zip(period_data, period_weights) if data
    ]
    if not valid_periods:
        raise ValueError("No valid data found in the specified time periods")

    selected_period_data, _ = random.choices(
        valid_periods, weights=[w for _, w in valid_periods], k=1
    )[0]

    # 選択された期間からランダムに1つ選択
    selected_data = random.choice(selected_period_data)
    return selected_data


def fetch_notion_page(id: str) -> dict:
    NOTION_API_KEY = os.environ["NOTION_API_KEY"]

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
    }

    url = f"https://api.notion.com/v1/blocks/{id}/children"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print(response.json())
        return response.json()
    else:
        raise Exception(
            f"status_code: {response.status_code}, message: {response.text}"
        )


# class NotionPage(pydantic.BaseModel):
#     content: list[NotionBlock]


class NotionBlock(pydantic.BaseModel):
    type: str
    plain_text: str


def convert_to_notion_blocks(data: dict) -> list[NotionBlock]:
    blocks = []
    for block in data["results"]:
        print("--------------------------------")
        print(block)
        block_type = block["type"]
        plain_text = ""
        if block_type in block and "rich_text" in block[block_type]:
            rich_text = block[block_type]["rich_text"]
            for text in rich_text:
                if "text" in text and "content" in text["text"]:
                    plain_text += text["text"]["content"]
        blocks.append(NotionBlock(type=block_type, plain_text=plain_text))
    return blocks


def convert_to_markdown(blocks: list[NotionBlock]) -> str:
    markdown = ""
    for block in blocks:
        if block.type == "heading_1":
            markdown += f"\n# {block.plain_text}\n"
        elif block.type == "heading_2":
            markdown += f"\n## {block.plain_text}\n"
        elif block.type == "heading_3":
            markdown += f"\n### {block.plain_text}\n"
        elif block.type == "bulleted_list_item":
            markdown += f"- {block.plain_text}\n"
        elif block.type == "numbered_list_item":
            markdown += f"1. {block.plain_text}\n"
        elif block.type == "divider":
            markdown += "\n---\n\n"
        elif block.type == "quote":
            markdown += f"> {block.plain_text}\n"
        else:
            markdown += f"{block.plain_text}\n"
    return markdown


# TODO
# - [x] NotionからDBのデータを取得する
# - [x] ページを一つ抽選する
# - [ ] ページの内容を取得する
# - [ ] ページの内容を要約して投稿内容にする
# - [ ] 投稿内容をJudgeする
# - [ ] 投稿内容を投稿する


def main():
    # data = fetch_notion_data()
    # notion_data_list = convert_to_notion_data(data)

    # selected_data = select_notion_data(notion_data_list)
    page = fetch_notion_page("1491137e613880698e94f273f43e042b")  # selected_data.id)
    # notion_page = convert_to_notion_page(page)
    blocks = convert_to_notion_blocks(page)
    markdown = convert_to_markdown(blocks)
    print(markdown)


if __name__ == "__main__":
    main()
