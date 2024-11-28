from notion_handler import NotionHandler

# TODO
# - [x] NotionからDBのデータを取得する
# - [x] ページを一つ抽選する
# - [x] ページの内容を取得する
# - [ ] ページの内容を要約して投稿内容にする
# - [ ] 投稿内容をJudgeする
# - [ ] 投稿内容を投稿する

# Refactor
# - [ ] 固定値やマジックナンバーを定数にする


def main():
    client = NotionHandler()
    data = client.fetch_notion_data()
    notion_data_list = client.convert_to_notion_data(data)
    selected_data = client.select_notion_data(notion_data_list)
    markdown = client.get_page_content(selected_data.id)
    print(markdown)


if __name__ == "__main__":
    main()
