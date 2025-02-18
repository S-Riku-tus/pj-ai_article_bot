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

TAGS = os.getenv("TAGS", "生成AI").split(",")

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
def fetch_qiita_articles(tags, qiita_api_token=API_TOKEN):
    """複数のタグに対応し、各タグごとに最新記事を取得"""
    url = 'https://qiita.com/api/v2/items'
    headers = {'Authorization': f'Bearer {qiita_api_token}'}
    all_articles = {}

    for tag in tags:
        params = {'query': f'tag:{tag}', 'page': 1, 'per_page': 3, 'sort': 'created'}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            articles = response.json()
            formatted_articles = [
                {
                    "title": article["title"],
                    "url": article["url"],
                    "description": clean_text(article["body"]),
                    "likes": article["likes_count"]
                }
                for article in articles
            ]
            all_articles[tag] = formatted_articles
        else:
            print(f"Error fetching articles for tag {tag}: {response.status_code}")
            all_articles[tag] = []

    return all_articles  # { "生成AI": [...], "Python": [...] }



# Slackにメッセージを送信する関数
client = WebClient(token=SLACK_TOKEN)


def send_message_to_slack(channel_id, title, url, description, likes, thread_ts=None):
    """Slackにメッセージを送信（スレッド対応）"""
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"📌 *タイトル : * {title}\n"
                        f"🔗 *URL : * {url}\n"
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


def notify_articles_to_slack():
    """複数のタグのQiita記事を取得し、Slackに投稿（タグごとにスレッド作成）"""
    articles_by_tag = fetch_qiita_articles(TAGS)

    for tag, articles in articles_by_tag.items():
        if not articles:
            print(f"No articles found for tag: {tag}")
            continue

        # タグごとの親メッセージ（スレッドの最初の投稿）
        parent_message = client.chat_postMessage(
            channel=SLACK_CHANNEL,
            text=f"📢 *最新のQiita記事まとめ - #{tag}*"
        )
        thread_ts = parent_message["ts"]

        # 各記事をスレッド内に投稿
        for article in articles:
            send_message_to_slack(
                channel_id=SLACK_CHANNEL,
                title=article["title"],
                url=article["url"],
                description=article["description"],
                likes=article["likes"],
                thread_ts=thread_ts
            )


# スクリプト実行時に1回だけ実行
notify_articles_to_slack()
