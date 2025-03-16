import os
import json
import requests
import re
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# .env の読み込み
load_dotenv()

# 設定ファイルのパス（従来の設定ファイルのみ使用）
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
    # text フィールドも付与（フォールバック用）
    text_fallback = f"{title} - {url}"
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
            text=text_fallback,
            blocks=blocks,
            thread_ts=thread_ts
        )
        print(f"Message sent: {response['message']['ts']}")
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")

# Slack チャンネル内で最新の親投稿のスレッドから、投稿された3件の記事のURLを抽出する関数
def get_latest_parent_article_urls(channel_id):
    try:
        # チャンネルの直近20件のメッセージを取得
        result = client.conversations_history(channel=channel_id, limit=20)
        messages = result.get('messages', [])
        # 親投稿（スレッドの開始投稿）で、「最新のQiita記事まとめ - #」というテキストが含まれるものを抽出
        parent_messages = [
            m for m in messages 
            if ("📢 *最新のQiita記事まとめ" in m.get('text', ''))
            and (("thread_ts" not in m) or (m.get('thread_ts') == m.get('ts')))
        ]
        if not parent_messages:
            return set()
        # 最新の親投稿（最も新しいもの）を選ぶ
        parent_messages.sort(key=lambda m: float(m['ts']), reverse=True)
        target_message = parent_messages[0]
        
        # 対象の親投稿のスレッド（返信）を取得。親投稿自体は除外する
        replies_result = client.conversations_replies(
            channel=channel_id,
            ts=target_message['ts'],
            limit=10
        )
        replies = replies_result.get('messages', [])
        article_urls = []
        for msg in replies:
            if msg.get('ts') == target_message['ts']:
                continue  # 親投稿は除外
            text = msg.get('text', '')
            # Qiita記事のURLを抽出（フォーマット例："🔗 *URL :* https://qiita.com/..."）
            match = re.search(r"🔗 \*URL :\* (\S+)", text)
            if match:
                article_urls.append(match.group(1))
            if len(article_urls) >= 3:
                break
        return set(article_urls)
    except SlackApiError as e:
        print(f"Error fetching latest parent message: {e.response['error']}")
        return set()

# Qiita記事をSlackに通知する関数（重複チェック＆通知付き）
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
            # 最新の親投稿から投稿された記事のURLを取得（前日の縛りなし）
            latest_article_urls = get_latest_parent_article_urls(slack_channel_id)

            # 今日の新規親投稿を作成し、スレッドを開始
            parent_message = client.chat_postMessage(
                channel=slack_channel_id,
                text=f"📢 *最新のQiita記事まとめ - #{tag}*"
            )
            thread_ts = parent_message["ts"]

            duplicate_articles = []  # 重複している記事情報を保持

            for article in articles:
                if article["url"] in latest_article_urls:
                    print(f"記事 {article['id']} は既に最新の親投稿にあります。スキップします。")
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

            # 重複記事がある場合、同じスレッドに通知を送信
            if duplicate_articles:
                duplicate_text = (
                    "⚠️ 重複記事通知: 以下の記事は既に最新の親投稿と重複しているため、今回の更新ではスキップされました。\n"
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

        except SlackApiError as e:
            print(f"Error sending parent message for {tag} in {slack_channel_id}: {e.response['error']}")

if __name__ == "__main__":
    notify_articles_to_slack()
