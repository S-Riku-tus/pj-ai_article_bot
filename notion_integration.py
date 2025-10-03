"""
Notion統合モジュール（後方互換性のため残存）
新しいコードでは src/services/notion_service.py を使用してください
"""
from src.services.notion_service import NotionService
from src.config import Config

# 後方互換性のための関数
def init_notion_client():
    """後方互換性のための関数"""
    config = Config()
    notion_service = NotionService(config)
    return notion_service.init_notion_client()

def create_or_update_notion_summary(articles_by_tag, existing_article_urls=None):
    """後方互換性のための関数"""
    config = Config()
    notion_service = NotionService(config)
    return notion_service.create_or_update_notion_summary(articles_by_tag, existing_article_urls)

def get_existing_notion_article_urls():
    """後方互換性のための関数"""
    config = Config()
    notion_service = NotionService(config)
    return notion_service.get_existing_notion_article_urls()