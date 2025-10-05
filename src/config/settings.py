"""
設定管理モジュール
環境変数と設定ファイルの管理を行う
"""
import os
import json
from dotenv import load_dotenv, find_dotenv
from typing import List, Dict


class Config:
    """設定管理クラス"""
    
    def __init__(self):
        # .env の読み込み（強制的に再読み込み）
        load_dotenv(find_dotenv(), override=True)
        
        # 設定ファイルのパス
        self.CONFIG_FILE = "config.json"
        
        # 設定の読み込み
        self._load_config()
        self._load_environment_variables()
        self._validate_config()
    
    def _load_config(self):
        """設定ファイルを読み込む"""
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                self.tags = config_data.get("tags", ["生成AI", "Python", "LLM"])
        else:
            self.tags = ["生成AI", "Python", "LLM"]  # デフォルト値
        
        # タグの優先順位（配列の順番が優先順位を表す）
        self.tag_priority = self.tags.copy()
    
    def _load_environment_variables(self):
        """環境変数を読み込む"""
        self.slack_token = os.getenv("SLACK_TOKEN")
        self.qiita_api_token = os.getenv("API_TOKEN")  # Qiita APIトークン
        
        # Slackチャンネル設定
        slack_channels = os.getenv("SLACK_CHANNELS", "")
        self.tag_channel_map = self._parse_slack_channels(slack_channels)
    
    def _parse_slack_channels(self, slack_channels: str) -> Dict[str, str]:
        """Slackチャンネル設定を解析してタグごとのチャンネルIDマッピングを取得"""
        tag_channel_map = {}
        if not slack_channels:
            return tag_channel_map
        
        pairs = slack_channels.split(",")
        for pair in pairs:
            parts = pair.split(":")
            if len(parts) == 2:
                tag, channel_id = parts
                tag_channel_map[tag.strip()] = channel_id.strip()
        
        return tag_channel_map
    
    def _validate_config(self):
        """設定の検証"""
        if not self.slack_token:
            raise ValueError("SLACK_TOKEN environment variable must be set.")
        
        if not self.qiita_api_token:
            raise ValueError("API_TOKEN (Qiita API token) environment variable must be set.")
        
        if not self.tag_channel_map:
            print("Warning: No valid Slack channel mapping found. "
                  "Please set SLACK_CHANNELS environment variable.")
        
        # 設定の診断
        print("Configuration loaded successfully.")
    
    def update_tags(self, new_tags: List[str]) -> List[str]:
        """タグを更新する"""
        self.tags = new_tags
        self.tag_priority = new_tags.copy()
        
        config = {"tags": new_tags}
        with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        return self.tags
