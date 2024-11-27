import os
import requests
import pydantic

NOTION_API_KEY = os.environ["NOTION_API_KEY"]
DATABASE_ID = 'decb8944082e473793322534544f4fcf'

headers = {
    'Authorization': f'Bearer {NOTION_API_KEY}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}

payload = {
    'sorts': [
        {
            'property': '作成日時',
            'direction': 'ascending'
        }
    ]
}

url = f'https://api.notion.com/v1/databases/{DATABASE_ID}/query'
response = requests.post(url, headers=headers, json=payload)

# レスポンスの確認
if response.status_code == 200:
    data = response.json()
    print(data)
else:
    print(f'エラーが発生しました: {response.status_code}')
    print(response.text)

# TODO
# - [ ] ページを一つ抽選する
# - [ ] ページの内容を取得する
# - [ ] ページの内容を要約して投稿内容にする
# - [ ] 投稿内容をJudgeする
# - [ ] 投稿内容を投稿する
