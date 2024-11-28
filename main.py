from langchain_handler import LangChainHandler
from notion_handler import NotionHandler
from tweet_handler import TweetHandler


def main():
    client = NotionHandler()
    data = client.fetch_notion_data()
    notion_data_list = client.convert_to_notion_data(data)
    selected_data = client.select_notion_data(notion_data_list)
    markdown = client.get_page_content(selected_data.id)
    # print(markdown)

    langchain_client = LangChainHandler()
    post = langchain_client.run_workflow(markdown)
    # print(post)

    tweet_client = TweetHandler()
    tweet_client.post_tweet(post)


if __name__ == "__main__":
    main()
