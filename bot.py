import os
import requests
import re
from bs4 import BeautifulSoup
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import schedule
import time
from dotenv import load_dotenv

load_dotenv()

# GitHub Actions の環境変数から取得
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")
API_TOKEN = os.getenv("API_TOKEN")

# トークンの確認
if not SLACK_TOKEN or not SLACK_CHANNEL or not API_TOKEN:
    raise ValueError("SLACK_TOKEN, SLACK_CHANNEL, and API_TOKEN environment variables must be set.")


# HTMLタグ & Markdownの整形関数
def clean_text(markdown_text):
    """QiitaのMarkdownをSlack用に整形"""

    # Qiitaのカスタムブロックのラベル（:::note warn など）を削除し、内容は保持
    markdown_text = re.sub(r":::\s*\w+\s*\n", "", markdown_text, flags=re.DOTALL)
    markdown_text = re.sub(r":::", "", markdown_text)  # 閉じタグの削除

    # HTMLタグを除去（BeautifulSoupを使用）
    soup = BeautifulSoup(markdown_text, "html.parser")
    text = soup.get_text()

    # Markdownの余計な記号を削除
    text = re.sub(r"^#+\s*(.*)", r"[*\1*]", text, flags=re.MULTILINE)  # 見出し（# 1. → 1.）
    text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)  # 強調（**bold** → bold）
    text = re.sub(r":メモ:", "", text)  # `:メモ:` の削除
    text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.MULTILINE)  # 残ったHTMLタグの削除（<dl>, <dt>など）

    # 余計な改行を整理
    text = re.sub(r"\n{2,}", "\n", text)  # 2つ以上の改行を1つに統一

    # 最初の200文字のみ取得
    return text[:200]


# Qiitaから最新3つの記事を取得する関数
def fetch_qiita_articles(tag='生成AI', qiita_api_token=API_TOKEN):
    url = 'https://qiita.com/api/v2/items'
    headers = {'Authorization': f'Bearer {qiita_api_token}'}
    params = {'query': f'tag:{tag}', 'page': 1, 'per_page': 3, 'sort': 'created'}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        articles = response.json()

        # 記事情報を加工
        formatted_articles = []
        for article in articles:
            formatted_articles.append({
                "title": article["title"],
                "url": article["url"],
                "description": clean_text(article["body"]),  # Markdownを整形
                "likes": article["likes_count"],
            })

        return formatted_articles
    else:
        print(f"Error fetching Qiita articles: {response.status_code}")
        return []


# Slackにメッセージを送信する関数
client = WebClient(token=SLACK_TOKEN)


def send_message_to_slack(channel_id, title, url, description, likes, thread_ts=None):
    """Slackにメッセージを送信（スレッド対応）"""
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"📌 *タイトル : * <{url}|{title}>\n"
                        f"👍 *LGTM数 : * {likes}\n"
                        f"📝 *概要 : * \n{description}...\n"
            }
        }
    ]

    try:
        response = client.chat_postMessage(
            channel=channel_id,
            blocks=blocks,
            thread_ts=thread_ts  # スレッドの親メッセージがある場合に適用
        )
        print(f"Message sent: {response['message']['ts']}")
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")


# Qiitaの記事をSlackに通知する関数
def notify_articles_to_slack():
    """Qiitaの記事を取得し、Slackに投稿（スレッド形式）"""
    articles = fetch_qiita_articles()

    if not articles:
        print("No articles found.")
        return

    # 親メッセージ（スレッドの最初の投稿）
    parent_message = client.chat_postMessage(
        channel=SLACK_CHANNEL,
        text="📢 *最新のQiita記事まとめ*",
    )

    # 親メッセージの `ts`（スレッドID）を取得
    thread_ts = parent_message["ts"]

    # 各記事をスレッド内に投稿
    for article in articles:
        send_message_to_slack(
            channel_id=SLACK_CHANNEL,
            title=article["title"],
            url=article["url"],
            description=article["description"],
            likes=article["likes"],
            thread_ts=thread_ts  # スレッドとして投稿
        )


# スクリプト実行時に1回だけ実行
notify_articles_to_slack()
