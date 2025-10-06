# Qiita Slack Bot

このプロジェクトは、Qiitaから特定のタグの最新記事を定期的にSlackに通知するボットです。
優先順位の高いタグから最も価値のある記事を選び、シンプルな形式で通知します。

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
```

## 使い方

```bash
python main.py
```

実行すると、設定したタグの最新Qiita記事を優先順位に従ってSlackに通知します。記事のタグ、タイトル、URLがシンプルな形式で通知されます。

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

## GitHub Actions による定期実行

このプロジェクトはGitHub Actionsを使用して定期実行されます。

### 実行スケジュール

- **毎日 08:00 JST** (UTC 23:00)
- **毎日 12:00 JST** (UTC 03:00)  
- **毎日 18:00 JST** (UTC 09:00)

### GitHub Secrets の設定

GitHubリポジトリの **Settings** → **Secrets and variables** → **Actions** で以下のSecretsを設定してください：

| Secret名 | 説明 | 例 |
|---------|------|-----|
| `SLACK_TOKEN` | Slack Bot Token | `xoxb-your-slack-bot-token` |
| `SLACK_CHANNELS` | チャンネル設定 | `生成AI:C12345678,Python:C87654321` |
| `API_TOKEN` | Qiita API Token | `your-qiita-api-token` |

### 手動実行

GitHub Actionsの **Actions** タブから **Qiita Slack Notifier** ワークフローを手動実行することも可能です。

### 実行ログの確認

GitHub Actionsの **Actions** タブで実行履歴とログを確認できます。
