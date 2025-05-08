# Qiita Slack Bot

このプロジェクトは、Qiitaから生成AI関連の記事を定期的にSlackに通知するボットです。
また、通知された記事を自動的にNotionにまとめる機能も追加されています。
※実際の通知は、指定した時間の数分～30分ほど遅れて来ます。

## インストール

以下のコマンドで依存ライブラリをインストールできます。

```bash
pip install -r requirements.txt

```

## 環境設定

以下の環境変数を `.env` ファイルに設定する必要があります：

```
SLACK_TOKEN=xoxb-your-slack-token
API_TOKEN=your-qiita-api-token
SLACK_CHANNELS=生成AI:C12345678,機械学習:C87654321

# Notion連携のための設定（オプション）
ENABLE_NOTION=true
NOTION_TOKEN=secret_your_notion_integration_token
NOTION_PAGE_ID=your_notion_parent_page_id
```

### Notion連携の設定方法

1. [Notion Developers](https://developers.notion.com/)にアクセスし、新しいインテグレーションを作成
2. インテグレーションのシークレットトークンを取得し、`NOTION_TOKEN`に設定
3. Notionで記事をまとめたいページを作成し、そのページIDを`NOTION_PAGE_ID`に設定
   - ページIDはページのURLから取得できます: `https://www.notion.so/workspace/[ページID]?v=...`
4. 作成したインテグレーションをページに接続（ページの「・・・」→「接続を追加」から）
5. `.env`ファイルの`ENABLE_NOTION`を`true`に設定

## 使い方

```bash
python bot.py
```

実行すると、設定したタグの最新Qiita記事をSlackに通知し、同時にNotionページに未読記事をまとめます。

Notionページには、タグごとにテーブル形式で記事がまとめられ、タイトル、URL、LGTM数が記録されます。
