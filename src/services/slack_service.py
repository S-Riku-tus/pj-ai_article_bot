"""
Slack通知サービス
Slackへのメッセージ送信、履歴管理、重複チェック機能
"""
import re
from datetime import datetime
from typing import Dict, Any, Optional, Set, List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from ..config.settings import Config
from ..utils.formatters import format_latex_for_slack
from .ai_service import AIService


class SlackService:
    """Slack通知サービス"""
    
    def __init__(self, config: Config, ai_service: AIService):
        self.config = config
        self.ai_service = ai_service
        self.tag_channel_map = config.tag_channel_map
        self.client = WebClient(token=config.slack_token)
    
    def notify_articles(self, articles_by_tag: Dict[str, List[Dict[str, Any]]]) -> bool:
        """記事をSlackに通知する"""
        success_count = 0
        
        for tag, articles in articles_by_tag.items():
            if not articles:
                print(f"No articles found for tag: {tag}")
                continue

            slack_channel_id = self.tag_channel_map.get(tag)
            if not slack_channel_id:
                print(f"❌ Error: チャンネルIDが見つかりません: {tag}")
                continue

            try:
                # 最新の親投稿から投稿された記事のURLを取得
                latest_article_urls = self._get_latest_parent_article_urls(slack_channel_id)

                # 今日の新規親投稿を作成し、スレッドを開始
                parent_response = self.client.chat_postMessage(
                    channel=slack_channel_id,
                    text=f"📢 *最新のQiita記事まとめ - #{tag} - {datetime.now().strftime('%Y-%m-%d')}*"
                )
                thread_ts = parent_response['ts']

                duplicate_articles = []  # 重複している記事情報を保持

                for article in articles:
                    if article["url"] in latest_article_urls:
                        print(f"記事 {article['id']} は既に最新の親投稿にあります。スキップします。")
                        duplicate_articles.append(f"*{article['title']}* (<{article['url']}>)")
                        continue

                    # 記事をSlackに送信
                    self._send_message_to_slack(
                        channel_id=slack_channel_id,
                        article=article,
                        thread_ts=thread_ts
                    )

                # 重複記事がある場合、同じスレッドに通知を送信
                if duplicate_articles:
                    duplicate_text = (
                        "⚠️ 重複記事通知: 以下の記事は既に最新の親投稿と重複しているため、今回の更新ではスキップされました。\n"
                        + "\n".join(duplicate_articles)
                    )
                    self._send_message_to_slack(
                        channel_id=slack_channel_id,
                        article={
                            "title": "重複記事通知",
                            "url": "",
                            "description": duplicate_text,
                            "likes": 0,
                            "user": "system"
                        },
                        thread_ts=thread_ts
                    )
                
                success_count += 1

            except SlackApiError as e:
                print(f"Error sending parent message for {tag} in {slack_channel_id}: {e.response['error']}")
        
        return success_count > 0
    
    def _send_message_to_slack(self, channel_id: str, article: Dict[str, Any], thread_ts: Optional[str] = None) -> Optional[str]:
        """Slack にメッセージを送信する"""
        # 記事の翻訳・要約を取得
        try:
            translation = self.ai_service.translate_and_summarize_article(article)
            
            # text フィールドも付与（フォールバック用）
            text_fallback = f"{translation['translated_title']} - {article['url']}"
            
            # 数式表記のクリーニング（LaTeX形式の数式を適切に表示）
            title = format_latex_for_slack(article['title'])
            translated_title = format_latex_for_slack(translation['translated_title'])
            translated_summary = format_latex_for_slack(translation['translated_summary'])
            key_points = format_latex_for_slack(translation['key_points'])
            
            # Slack用に改行とフォーマットを改善したブロック
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*【タイトル】*\n{translated_title}\n\n*【原題】*\n{title}\n\n*【著者】*\n{article['user']}\n\n*【LGTM数】*\n{article['likes']}\n\n*【URL】*\n{article['url']}\n\n*【重要なポイント】*\n{key_points}\n\n*【要約】*\n{translated_summary}"
                    }
                }
            ]
        except Exception as e:
            print(f"Error preparing message: {e}")
            # エラーが発生した場合は元の記事情報のみを表示
            text_fallback = f"{article['title']} - {article['url']}"
            
            title = format_latex_for_slack(article['title'])
            description = format_latex_for_slack(article['description'])
            
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*【タイトル】*\n{title}\n\n*【著者】*\n{article['user']}\n\n*【LGTM数】*\n{article['likes']}\n\n*【URL】*\n{article['url']}\n\n*【概要】*\n{description}..."
                    }
                }
            ]
        
        try:
            response = self.client.chat_postMessage(
                channel=channel_id,
                text=text_fallback,
                blocks=blocks,
                thread_ts=thread_ts
            )
            print(f"Message sent: {response['ts']}")
            return response['ts']
        except SlackApiError as e:
            print(f"Error sending message: {e.response['error']}")
            return None
    
    def _get_latest_parent_article_urls(self, channel_id: str) -> Set[str]:
        """Slack チャンネル内で最新の親投稿のスレッドから、投稿された記事のURLを抽出する"""
        try:
            # チャンネルの直近20件のメッセージを取得
            result = self.client.conversations_history(channel=channel_id, limit=20)
            messages = result.get('messages', [])
            # 親投稿（スレッドの開始投稿）で、「最新のQiita記事まとめ」というテキストが含まれるものを抽出
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
            replies_result = self.client.conversations_replies(
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
                # Qiita記事のURLを抽出（フォーマット例："🔗 *URL:* https://qiita.com/..."）
                match = re.search(r"URL:.*?https://qiita\.com/[^\s\">]+", text)
                if match:
                    # URL部分だけを抽出
                    url_text = match.group(0)
                    url = re.search(r'https://[^\s">]+', url_text).group(0)
                    article_urls.append(url)
            
            print(f"Found {len(article_urls)} existing article URLs in the latest thread")
            return set(article_urls)
        except SlackApiError as e:
            print(f"Error fetching latest parent message: {e.response['error']}")
            return set()
