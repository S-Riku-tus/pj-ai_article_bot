# Qiita Slack Bot

このプロジェクトは、Qiitaから特定のタグの最新記事を定期的にSlackに通知するボットです。
優先順位の高いタグから最も価値のある記事を選び、シンプルな形式で通知します。
また、通知された記事を自動的にNotionにまとめる機能も追加されています。

## インストール

以下のコマンドで依存ライブラリをインストールできます。

```bash
pip install -r requirements.txt

```

## 環境設定

以下の環境変数を `.env` ファイルに設定する必要があります：

```
# Slackトークン（必須）
SLACK_TOKEN=xoxb-your-slack-token

# Qiita APIトークン（必須）
API_TOKEN=your-qiita-api-token

# 通知先チャンネル（必須）
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
python main.py
```

実行すると、設定したタグの最新Qiita記事を優先順位に従ってSlackに通知します。記事のタグ、タイトル、URLがシンプルな形式で通知されます。同時にNotionページに未読記事をまとめます。

### タグの優先順位

configファイル内のタグの順序が優先順位を表します。例えば、デフォルト設定の場合：

```json
{
    "tags": ["生成AI", "Python", "LLM"]
}
```

この設定では、生成AIが最も優先度が高く、次にPython、最後にLLMとなります。
ボットは各タグから最新の記事を取得し、優先度の高いものから順に通知します。

### APIキーの設定

#### Qiita API
1. [Qiita API](https://qiita.com/api/v2/docs)からアクセストークンを取得
2. 取得したトークンを`.env`ファイルの`API_TOKEN`に設定

Notionページには、タグごとにテーブル形式で記事がまとめられ、タイトル、URL、LGTM数、著者が記録されます。
