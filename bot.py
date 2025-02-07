import os
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import schedule
import time
from dotenv import load_dotenv

load_dotenv()

# .envファイルからトークンとIDを取得
SLACK_TOKEN = os.environ.get("SLACK_TOKEN")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL")
API_TOKEN = os.environ.get("API_TOKEN")

# トークンとIDが設定されているか確認
if not SLACK_TOKEN or not SLACK_CHANNEL or not API_TOKEN:
    raise ValueError("SLACK_TOKEN, SLACK_CHANNEL, and API_TOKEN environment variables must be set.")


# Qiitaから最新3つの記事を取得する関数
def fetch_qiita_articles(tag='生成AI', qiita_api_token=API_TOKEN):
    # Qiita APIのエンドポイント
    url = 'https://qiita.com/api/v2/items'

    # APIリクエストのヘッダーにトークンを追加
    headers = {
        'Authorization': f'Bearer {qiita_api_token}'  # 渡されたトークンを使用
    }

    # パラメータ設定
    params = {
        'query': f'tag:{tag}',  # タグに基づく記事検索
        'page': 1,              # 1ページ目
        'per_page': 3,          # 最新の3件の記事を取得
        'sort': 'created',      # 記事の作成日時でソート（新しい順）
    }

    # APIリクエストを送信
    response = requests.get(url, headers=headers, params=params)

    # ステータスコードとレスポンス内容を表示
    print(f"Status Code: {response.status_code}")  # ステータスコードを表示
    if response.status_code == 200:
        try:
            # JSONレスポンスを取得
            articles = response.json()
            # 各記事のタイトルとURLを表示
            for article in articles:
                print(f"Title: {article['title']}")
                print(f"URL: {article['url']}")
            return articles  # 記事情報を返す
        except ValueError:
            print("Error: Response is not in JSON format.")
            return []
    else:
        print(f"Error fetching Qiita articles: {response.status_code}")
        print(f"Response Text: {response.text}")
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
def notify_articles_to_slack(channel_id, api_token, tag='AI'):
    articles = fetch_qiita_articles(tag, api_token)
    if articles:
        for article in articles:
            title = article['title']
            url = article['url']
            message = f"🔍 新しい記事があります: {title}\n🔗 {url}"
            send_message_to_slack(channel_id, message)
    else:
        print("No articles found.")


# 毎日8:30に実行
schedule.every().day.at("04:50").do(lambda: notify_articles_to_slack(SLACK_CHANNEL, API_TOKEN))


while True:
    schedule.run_pending()
    time.sleep(1)
