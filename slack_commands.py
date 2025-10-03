from flask import Flask, request, jsonify
import subprocess
from src.config import Config

app = Flask(__name__)
config = Config()
client = WebClient(token=config.slack_token)
CONFIG_FILE = "config.json"


def commit_and_push_changes():
    """GitHub に `config.json` の変更を push する"""
    try:
        subprocess.run(["git", "config", "--global", "user.email", "bot@example.com"], check=True)
        subprocess.run(["git", "config", "--global", "user.name", "SlackBot"], check=True)
        subprocess.run(["git", "add", "config.json"], check=True)
        subprocess.run(["git", "commit", "-m", "Update config.json via Slack command"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ config.json を GitHub に push しました")
    except subprocess.CalledProcessError as e:
        print(f"❌ GitHub への push に失敗しました: {e}")


def load_config():
    return {"tags": config.tags}


def save_config(data):
    config.update_tags(data["tags"])


@app.route("/slack/set_tags", methods=["POST"])
def set_tags():
    data = request.form
    user_input = data.get("text", "").strip()

    if not user_input:
        return jsonify({"text": "⚠️ 設定するタグを指定してください！"}), 200

    new_tags = [tag.strip() for tag in user_input.split(",")]
    config = load_config()
    config["tags"] = new_tags
    save_config(config)

    commit_and_push_changes()  # 🔹 GitHub に変更を push

    response_text = f"✅ `TAGS` を更新しました！\n現在のタグ: `{', '.join(new_tags)}`"
    return jsonify({"text": response_text}), 200


if __name__ == "__main__":
    app.run(port=5000)
