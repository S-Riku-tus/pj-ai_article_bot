"""
AI翻訳・要約サービス
Gemini APIを使用した記事の翻訳・要約機能
"""
import re
import google.generativeai as genai
from typing import Dict, Any
from ..config.settings import Config


class AIService:
    """AI翻訳・要約サービス（Gemini専用）"""
    
    def __init__(self, config: Config):
        self.config = config
        self.gemini_api_key = config.gemini_api_key
        
        # API設定
        self._setup_gemini()
    
    def _setup_gemini(self):
        """Gemini APIの設定"""
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            print("Using Gemini API for translation and summarization")
        else:
            print("Warning: Gemini API key is not set. Translation features will be disabled.")
    
    def translate_and_summarize_article(self, article: Dict[str, Any]) -> Dict[str, str]:
        """Gemini APIを使って記事を翻訳・要約する"""
        if not self.gemini_api_key:
            return {
                "translated_title": article["title"],
                "translated_summary": "Gemini API key is not set. Translation unavailable.",
                "key_points": "Gemini API key is not set. Key points unavailable."
            }
        
        return self._translate_and_summarize_article_gemini(article)
    
    def _translate_and_summarize_article_gemini(self, article: Dict[str, Any]) -> Dict[str, str]:
        """Gemini APIを使って記事を翻訳・要約する"""
        if not self.gemini_api_key:
            return {
                "translated_title": article["title"],
                "translated_summary": "Gemini API key is not set. Translation unavailable.",
                "key_points": "Gemini API key is not set. Key points unavailable."
            }
        
        try:
            # プロンプトを作成
            prompt = f"""以下のQiita記事の情報を日本語に翻訳し、要約してください。

記事タイトル: {article['title']}
著者: {article['user']}
作成日: {article['created_at']}
LGTM数: {article['likes']}

記事内容:
{article['description']}

以下の3つの部分に分けて出力してください:
1. 日本語タイトル:
（ここに日本語タイトルを記入）

2. 日本語要約:
（ここに300-500文字の日本語要約を記入）

3. 重要なポイント:
- （重要なポイント1）
- （重要なポイント2）
- （重要なポイント3）
（3-5個の重要なポイントを作成してください）
"""
            
            # Gemini APIを呼び出し
            model = genai.GenerativeModel('gemini-2.0-flash-lite')
            response = model.generate_content(prompt)
            
            # レスポンスから結果を取得
            result = response.text
            
            return self._parse_ai_response(result, article)
            
        except Exception as e:
            print(f"Error translating and summarizing article with Gemini: {e}")
            return {
                "translated_title": article["title"],
                "translated_summary": f"翻訳・要約中にエラーが発生しました: {str(e)}",
                "key_points": "重要なポイントは利用できません。"
            }
    
    def _parse_ai_response(self, result: str, article: Dict[str, Any]) -> Dict[str, str]:
        """AI レスポンスを解析して各セクションを抽出"""
        # 結果を解析（パターンマッチングで各セクションを抽出）
        title_match = re.search(
            r'1\.\s*日本語タイトル:\s*(.+?)(?=\n\n|\n2\.)', 
            result, 
            re.DOTALL
        )
        summary_match = re.search(
            r'2\.\s*日本語要約:\s*(.+?)(?=\n\n|\n3\.)', 
            result, 
            re.DOTALL
        )
        points_match = re.search(r'3\.\s*重要なポイント:\s*(.+)', result, re.DOTALL)
        
        translated_title = title_match.group(1).strip() if title_match else article["title"]
        translated_summary = summary_match.group(1).strip() if summary_match else "要約の生成に失敗しました。"
        key_points = points_match.group(1).strip() if points_match else "重要なポイントの生成に失敗しました。"
        
        return {
            "translated_title": translated_title,
            "translated_summary": translated_summary,
            "key_points": key_points
        }
