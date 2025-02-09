import os
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import schedule
import time
from dotenv import load_dotenv

load_dotenv()

# # (デバッグ用).envファイルからトークンとIDを取得
# SLACK_TOKEN = os.environ.get("SLACK_TOKEN")
# SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL")
# API_TOKEN = os.environ.get("API_TOKEN")

# GitHub Actions の環境変数から取得
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")
API_TOKEN = os.getenv("API_TOKEN")

# トークンの確認
if not SLACK_TOKEN or not SLACK_CHANNEL or not API_TOKEN:
    raise ValueError("SLACK_TOKEN, SLACK_CHANNEL, and API_TOKEN environment variables must be set.")


# Qiitaから最新3つの記事を取得する関数
def fetch_qiita_articles(tag='生成AI', qiita_api_token=API_TOKEN):
    url = 'https://qiita.com/api/v2/items'
    headers = {'Authorization': f'Bearer {qiita_api_token}'}
    params = {'query': f'tag:{tag}', 'page': 1, 'per_page': 3, 'sort': 'created'}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching Qiita articles: {response.status_code}")
        return []


# Slackにメッセージを送信する関数
client = WebClient(token=SLACK_TOKEN)


def send_message_to_slack(channel_id, message):
    try:
        response = client.chat_postMessage(channel=channel_id, text=message)
        print(f"Message sent: {response['message']['text']}")
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")


# Qiitaの記事をSlackに通知する関数
def notify_articles_to_slack():
    articles = fetch_qiita_articles()
    if articles:
        for article in articles:
            message = f"🔍 新しい記事があります: {article['title']}\n🔗 {article['url']}"
            send_message_to_slack(SLACK_CHANNEL, message)
    else:
        print("No articles found.")


# # デバッグ用
# schedule.every().day.at("13:50").do(lambda: notify_articles_to_slack(SLACK_CHANNEL, API_TOKEN))


# 🔹 スクリプト実行時に1回だけ実行
notify_articles_to_slack()
