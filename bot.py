import os
import json
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# .env の読み込み
load_dotenv()

# 設定ファイルと投稿済み記事ファイルのパス
CONFIG_FILE = "config.json"
POSTED_FILE = "posted_articles.json"

# 設定ファイルを読み込む関数
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"tags": ["生成AI"]}  # デフォルト値

# 過去に投稿した記事のIDを読み込む関数
def load_posted_articles():
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

# 投稿済み記事のIDを保存する関数
def save_posted_articles(posted_ids):
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(posted_ids), f, ensure_ascii=False, indent=4)

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

# Slack クライアントの作成
client = WebClient(token=SLACK_TOKEN)

# Qiita API から記事を取得する関数
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
                    "id": article["id"],  # Qiitaの一意のID
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

# Slack にメッセージを送信する関数
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

# Qiita記事をSlackに通知する関数（重複チェック＆通知付き）
def notify_articles_to_slack():
    articles_by_tag = fetch_qiita_articles(TAGS)
    posted_ids = load_posted_articles()  # 過去に投稿済みのIDを読み込む

    for tag, articles in articles_by_tag.items():
        if not articles:
            print(f"No articles found for tag: {tag}")
            continue

        slack_channel_id = TAG_CHANNEL_MAP.get(tag)
        if not slack_channel_id:
            print(f"❌ Error: チャンネルIDが見つかりません: {tag}")
            continue

        try:
            # 親メッセージを投稿してスレッドを開始
            parent_message = client.chat_postMessage(
                channel=slack_channel_id,
                text=f"📢 *最新のQiita記事まとめ - #{tag}*"
            )
            thread_ts = parent_message["ts"]

            duplicate_articles = []  # 重複している記事情報を保持

            for article in articles:
                if article["id"] in posted_ids:
                    print(f"記事 {article['id']} は既に投稿済みです。スキップします。")
                    duplicate_articles.append(f"*{article['title']}* (<{article['url']}>)")
                    continue

                send_message_to_slack(
                    channel_id=slack_channel_id,
                    title=article["title"],
                    url=article["url"],
                    description=article["description"],
                    likes=article["likes"],
                    thread_ts=thread_ts
                )
                posted_ids.add(article["id"])

            # 重複記事がある場合、同じスレッドに通知を送信
            if duplicate_articles:
                duplicate_text = (
                    "⚠️ 重複記事通知: 以下の記事は既に投稿済みのため、今回の更新ではスキップされました。\n"
                    + "\n".join(duplicate_articles)
                )
                send_message_to_slack(
                    channel_id=slack_channel_id,
                    title="重複記事通知",
                    url="",
                    description=duplicate_text,
                    likes=0,
                    thread_ts=thread_ts
                )

            # 更新後の投稿済み記事IDを保存
            save_posted_articles(posted_ids)

        except SlackApiError as e:
            print(f"Error sending parent message for {tag} in {slack_channel_id}: {e.response['error']}")

if __name__ == "__main__":
    notify_articles_to_slack()
