"""
Qiita記事取得サービス
Qiitaから記事を取得し、選択ロジックを提供する
"""
import requests
from typing import Dict, List, Any
from ..config.settings import Config


class QiitaService:
    """Qiita記事取得サービス"""
    
    def __init__(self, config: Config):
        self.config = config
        self.tags = config.tags
        self.tag_priority = config.tag_priority
        self.qiita_api_token = config.qiita_api_token
        self.base_url = 'https://qiita.com/api/v2/items'
    
    def fetch_qiita_articles(self) -> Dict[str, List[Dict[str, Any]]]:
        """各タグにつき最新の記事を取得する"""
        all_articles = {}
        
        for tag in self.tags:
            try:
                headers = {'Authorization': f'Bearer {self.qiita_api_token}'}
                params = {
                    'query': f'tag:{tag}',
                    'page': 1,
                    'per_page': 1,  # 各タグで最新の1件のみ取得
                    'sort': 'created'
                }
                
                response = requests.get(self.base_url, headers=headers, params=params)
                
                if response.status_code == 200:
                    articles = response.json()
                    formatted_articles = []
                    
                    for article in articles:
                        article_info = {
                            "id": article["id"],
                            "title": article["title"],
                            "url": article["url"],
                            "description": article["body"][:200],  # 最初の200文字
                            "likes": article["likes_count"],
                            "tag": tag,  # タグ情報を追加
                            "created_at": article["created_at"],
                            "user": article["user"]["id"]
                        }
                        formatted_articles.append(article_info)
                    
                    all_articles[tag] = formatted_articles
                    print(f"Found {len(formatted_articles)} articles for tag {tag}")
                else:
                    print(f"Error fetching articles for tag {tag}: {response.status_code}")
                    all_articles[tag] = []
                    
            except Exception as e:
                print(f"Error fetching articles for tag {tag}: {e}")
                all_articles[tag] = []
        
        return all_articles
    
    def select_best_articles(self, articles_by_tag: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        優先順位の高いカテゴリから順に記事を選択し、各タグから最適な記事を返す
        
        Args:
            articles_by_tag (dict): タグごとの記事リスト
        
        Returns:
            dict: タグごとの選択された記事リスト
        """
        selected_articles = {}
        
        for tag in self.tag_priority:
            if tag in articles_by_tag and articles_by_tag[tag]:
                # 各タグから最新の1件の記事を選択
                articles = articles_by_tag[tag]
                selected_articles[tag] = articles[:1]  # 最新の1件を選択
        
        return selected_articles
    
    def has_articles(self, articles_by_tag: Dict[str, List[Dict[str, Any]]]) -> bool:
        """記事が存在するかチェック"""
        return any(len(articles) > 0 for articles in articles_by_tag.values())
