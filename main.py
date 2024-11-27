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
        raise StandardError(
            f"status_code: {response.status_code}, message: {response.text}"
        )


class NotionData(pydantic.BaseModel):
    title: str
    created_time: datetime.datetime


def convert_to_notion_data(data: dict) -> list[NotionData]:
    notion_data_list = []
    for page in data["results"]:
        title = page["properties"]["名前"]["title"][0]["text"]["content"]
        created_time = datetime.datetime.fromisoformat(
            page["created_time"].replace("Z", "+00:00")
        )
        notion_data = NotionData(title=title, created_time=created_time)
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


# TODO
# - [x] NotionからDBのデータを取得する
# - [x] ページを一つ抽選する
# - [ ] ページの内容を取得する
# - [ ] ページの内容を要約して投稿内容にする
# - [ ] 投稿内容をJudgeする
# - [ ] 投稿内容を投稿する


def main():
    data = fetch_notion_data()
    notion_data_list = convert_to_notion_data(data)

    # for notion_data in notion_data_list:
    #     print(f"タイトル: {notion_data.title}")
    #     print(f"作成日時: {notion_data.created_time}")
    #     print("---")

    selected_data = select_notion_data(notion_data_list)
    print(f"タイトル: {selected_data.title}")
    print(f"作成日時: {selected_data.created_time}")


if __name__ == "__main__":
    main()
