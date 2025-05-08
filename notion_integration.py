import os
import json
from datetime import datetime
from notion_client import Client
from dotenv import load_dotenv

# .env の読み込み
load_dotenv()

# Notion APIトークンとデータベースID
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")  # Qiita記事をまとめるページのID

# Notion クライアントの初期化
notion = Client(auth=NOTION_TOKEN) if NOTION_TOKEN else None

def init_notion_client():
    """Notion クライアントが正しく初期化されているか確認"""
    global notion, NOTION_TOKEN, NOTION_PAGE_ID
    
    if not NOTION_TOKEN:
        print("⚠️ NOTION_TOKEN が設定されていません。")
        return False
        
    if not NOTION_PAGE_ID:
        print("⚠️ NOTION_PAGE_ID が設定されていません。")
        return False
        
    try:
        # Notionに接続テスト
        notion.pages.retrieve(NOTION_PAGE_ID)
        return True
    except Exception as e:
        print(f"❌ Notion APIへの接続に失敗しました: {e}")
        return False

def create_or_update_notion_summary(articles_by_tag, existing_article_urls=None):
    """Notionページに未読Qiita記事をまとめる
    
    Args:
        articles_by_tag (dict): タグごとの記事一覧
        existing_article_urls (set, optional): 既存の記事URL一覧
    """
    if not init_notion_client():
        return False
        
    if existing_article_urls is None:
        existing_article_urls = set()
    
    # 今日の日付を取得
    today = datetime.now().strftime("%Y年%m月%d日")
    
    # 今日の日付のタイトルを持つページを作成または更新
    page_title = f"Qiita未読記事まとめ - {today}"
    
    try:
        # 親ページの子ページを検索
        children = notion.blocks.children.list(NOTION_PAGE_ID)
        
        # 同じタイトルの子ページがあるか確認
        target_page_id = None
        for child in children.get("results", []):
            if child.get("type") == "child_page" and child.get("child_page", {}).get("title") == page_title:
                target_page_id = child.get("id")
                break
        
        # ページが存在しない場合は新規作成
        if not target_page_id:
            new_page = notion.pages.create(
                parent={"type": "page_id", "page_id": NOTION_PAGE_ID},
                properties={
                    "title": {"title": [{"text": {"content": page_title}}]}
                }
            )
            target_page_id = new_page["id"]
            # ページを初期化（説明を追加）
            notion.blocks.children.append(
                target_page_id,
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "今日中にチェックすべきQiita記事のまとめです。各タグごとにデータベース形式で整理されています。"
                                    }
                                }
                            ]
                        }
                    }
                ]
            )
        
        # タグごとにブロックを追加
        for tag, articles in articles_by_tag.items():
            # 新しい記事のみをフィルタリング
            new_articles = [article for article in articles if article["url"] not in existing_article_urls]
            
            if not new_articles:
                continue
                
            # タグのセクションを追加
            blocks = [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": f"#{tag} の記事"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "table",
                    "table": {
                        "table_width": 3,
                        "has_column_header": True,
                        "has_row_header": False,
                        "children": [
                            {
                                "type": "table_row",
                                "table_row": {
                                    "cells": [
                                        [{"type": "text", "text": {"content": "タイトル"}}],
                                        [{"type": "text", "text": {"content": "URL"}}],
                                        [{"type": "text", "text": {"content": "LGTM数"}}]
                                    ]
                                }
                            }
                        ]
                    }
                }
            ]
            
            # 記事ごとに行を追加
            for article in new_articles:
                row = {
                    "type": "table_row",
                    "table_row": {
                        "cells": [
                            [{"type": "text", "text": {"content": article["title"]}}],
                            [{"type": "text", "text": {"content": article["url"], "link": {"url": article["url"]}}}],
                            [{"type": "text", "text": {"content": str(article["likes"])}}]
                        ]
                    }
                }
                blocks[1]["table"]["children"].append(row)
            
            # ページにブロックを追加
            notion.blocks.children.append(target_page_id, children=blocks)
        
        return True
    except Exception as e:
        print(f"❌ Notionページの作成/更新に失敗しました: {e}")
        return False

def get_existing_notion_article_urls():
    """Notionの既存ページから記事URLを取得"""
    if not init_notion_client():
        return set()
    
    try:
        existing_urls = set()
        # 親ページの子ページをすべて取得
        children = notion.blocks.children.list(NOTION_PAGE_ID)
        
        for child in children.get("results", []):
            if child.get("type") == "child_page":
                page_id = child.get("id")
                # 子ページの内容を取得
                page_content = notion.blocks.children.list(page_id)
                
                # すべてのブロックから表を探し、URLを抽出
                for block in page_content.get("results", []):
                    if block.get("type") == "table":
                        table_id = block.get("id")
                        table_rows = notion.blocks.children.list(table_id).get("results", [])
                        
                        for row in table_rows:
                            if row.get("type") == "table_row":
                                cells = row.get("table_row", {}).get("cells", [])
                                if len(cells) >= 2:  # URLは2列目にあると仮定
                                    for text_obj in cells[1]:
                                        if text_obj.get("type") == "text" and text_obj.get("text", {}).get("link"):
                                            existing_urls.add(text_obj["text"]["link"]["url"])
        
        return existing_urls
    except Exception as e:
        print(f"❌ 既存記事URLの取得に失敗しました: {e}")
        return set() 