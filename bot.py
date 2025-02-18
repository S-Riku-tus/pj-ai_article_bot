import os
import requests
import re
from bs4 import BeautifulSoup
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import schedule
import time
from dotenv import load_dotenv

# .env の読み込み
load_dotenv()

# 環境変数の取得
TAGS = os.getenv("TAGS", "生成AI").split(",")
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
API_TOKEN = os.getenv("API_TOKEN")
SLACK_CHANNELS = os.getenv("SLACK_CHANNELS", "")

# 環境変数のバリデーション
if not SLACK_TOKEN or not API_TOKEN:
    raise ValueError("SLACK_TOKEN, SLACK_CHANNEL, and API_TOKEN environment variables must be set.")

# タグごとのチャンネルIDマッピングを作成
TAG_CHANNEL_MAP = {}
if SLACK_CHANNELS:
    pairs = SLACK_CHANNELS.split(",")
    for pair in pairs:
        tag, channel_id = pair.split(":")
        TAG_CHANNEL_MAP[tag.strip()] = channel_id.strip()

# Slack クライアント
client = WebClient(token=SLACK_TOKEN)


# HTMLタグ & Markdownの整形関数
def clean_text(markdown_text):
    """QiitaのMarkdownをSlack用に整形"""
    markdown_text = re.sub(r":::\s*\w+\s*\n", "", markdown_text, flags=re.DOTALL)
    markdown_text = re.sub(r":::", "", markdown_text)

    # HTMLタグを除去
    soup = BeautifulSoup(markdown_text, "html.parser")
    text = soup.get_text()

    # Markdownの整形
    text = re.sub(r"^#+\s*(.*)", r"[*\1*]", text, flags=re.MULTILINE)  # 見出し
    text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)  # 太字
    text = re.sub(r"\n{2,}", "\n", text)  # 改行調整

    return text[:200]  # 200文字以内に制限


# Qiita API から記事を取得
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


# Slack にメッセージを送信
def send_message_to_slack(channel_id, title, url, description, likes, thread_ts=None):
    """Slackにメッセージを送信（スレッド対応）"""
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
    """複数のタグのQiita記事を取得し、対応するSlackチャンネルに投稿"""
    articles_by_tag = fetch_qiita_articles(TAGS)

    print(articles_by_tag.keys())
    for tag, articles in articles_by_tag.items():
        if not articles:
            print(f"No articles found for tag: {tag}")
            continue

        # タグごとのSlackチャンネルID
        slack_channel_id = TAG_CHANNEL_MAP.get(tag)

        # タグごとの親メッセージ
        try:
            parent_message = client.chat_postMessage(
                channel=slack_channel_id,
                text=f"📢 *最新のQiita記事まとめ - #{tag}*"
            )
            thread_ts = parent_message["ts"]

            # 各記事をスレッド内に投稿
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
