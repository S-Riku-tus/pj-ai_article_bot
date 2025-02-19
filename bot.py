import os
import json
import requests
import re
from bs4 import BeautifulSoup
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# .env の読み込み
load_dotenv()

# 設定ファイルのパス
CONFIG_FILE = "config.json"


# 設定ファイルを読み込む関数
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"tags": ["生成AI"]}  # デフォルト値


# 設定の読み込み
config = load_config()
TAGS = config["tags"]

SLACK_TOKEN = os.getenv("SLACK_TOKEN")
API_TOKEN = os.getenv("API_TOKEN")
SLACK_CHANNELS = os.getenv("SLACK_CHANNELS", "")


if not SLACK_TOKEN or not API_TOKEN:
    raise ValueError("SLACK_TOKEN and API_TOKEN environment variables must be set.")

# タグごとのチャンネルIDマッピング
TAG_CHANNEL_MAP = {}
if SLACK_CHANNELS:
    pairs = SLACK_CHANNELS.split(",")
    for pair in pairs:
        tag, channel_id = pair.split(":")
        TAG_CHANNEL_MAP[tag.strip()] = channel_id.strip()

# Slack クライアント
client = WebClient(token=SLACK_TOKEN)


# Qiita API から記事を取得
def fetch_qiita_articles(tags):
    url = 'https://qiita.com/api/v2/items'
    headers = {'Authorization': f'Bearer {API_TOKEN}'}
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
                    "description": article["body"][:200],
                    "likes": article["likes_count"]
                }
                for article in articles
            ]
            all_articles[tag] = formatted_articles
        else:
            print(f"Error fetching articles for tag {tag}: {response.status_code}")
            all_articles[tag] = []
    return all_articles


# Slack にメッセージを送信
def send_message_to_slack(channel_id, title, url, description, likes, thread_ts=None):
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"📌 *タイトル :* {title}\n"
                        f"🔗 *URL :* {url}\n"
                        f"👍 *LGTM数 :* {likes}\n"
                        f"📝 *概要 :* \n{description}...\n"
            }
        }
    ]
    try:
        response = client.chat_postMessage(
            channel=channel_id,
            blocks=blocks,
            thread_ts=thread_ts
        )
        print(f"Message sent: {response['message']['ts']}")
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")


# Qiita記事をSlackに通知
def notify_articles_to_slack():
    articles_by_tag = fetch_qiita_articles(TAGS)

    for tag, articles in articles_by_tag.items():
        if not articles:
            print(f"No articles found for tag: {tag}")
            continue

        slack_channel_id = TAG_CHANNEL_MAP.get(tag)

        if not slack_channel_id:
            print(f"❌ Error: チャンネルIDが見つかりません: {tag}")
            continue

        try:
            parent_message = client.chat_postMessage(
                channel=slack_channel_id,
                text=f"📢 *最新のQiita記事まとめ - #{tag}*"
            )
            thread_ts = parent_message["ts"]

            for article in articles:
                send_message_to_slack(
                    channel_id=slack_channel_id,
                    title=article["title"],
                    url=article["url"],
                    description=article["description"],
                    likes=article["likes"],
                    thread_ts=thread_ts
                )

        except SlackApiError as e:
            print(f"Error sending parent message for {tag} in {slack_channel_id}: {e.response['error']}")


# スクリプト実行
notify_articles_to_slack()
