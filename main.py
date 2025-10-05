"""
Qiita記事通知Bot - メイン実行ファイル
ワークフローのみを記述し、詳細な処理は各サービスに委譲
"""
from src.config import Config
from src.services import QiitaService, SlackService


def main():
    """メイン実行関数"""
    try:
        # 設定の読み込み
        config = Config()
        
        # サービスの初期化
        qiita_service = QiitaService(config)
        slack_service = SlackService(config)
        
        # メインワークフロー
        print("🔍 Qiita記事を取得中...")
        articles_by_tag = qiita_service.fetch_qiita_articles()
        
        # 記事が見つかったかどうか
        if not qiita_service.has_articles(articles_by_tag):
            print("No articles found for any tag.")
            return
        
        # 優先順位に基づいて最適な記事を選択
        print("📋 最適な記事を選択中...")
        selected_articles = qiita_service.select_best_articles(articles_by_tag)
        
        if not selected_articles:
            print("No suitable articles found after priority filtering.")
            return
        
        # 選択した記事をSlackに通知
        print("📤 記事をSlackに通知中...")
        success = slack_service.notify_articles(selected_articles)
        
        if success:
            print("✅ Slack通知が完了しました。")
        else:
            print("❌ Slack通知に失敗しました。")
            
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        raise


if __name__ == "__main__":
    main()
