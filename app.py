# app.py
import os
import requests
from flask import Flask, jsonify, send_from_directory, request
import openai
from flask_cors import CORS
import env_production

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # クロスオリジンリクエストを許可

# 環境変数からAPIキーとリージョンを取得
AZURE_SPEECH_KEY = env_production.get_env_variable("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = env_production.get_env_variable("AZURE_SPEECH_REGION")
OPENAI_API_KEY = env_production.get_env_variable("OPENAI_API_KEY")

@app.route("/")
def index():
    # ルートアクセスで static/index.html を返す
    return send_from_directory("static", "index.html")

@app.route("/token", methods=["GET"])
def get_speech_token():
    """
    Azure Speech 用の一時トークンを取得して返すエンドポイント。
    """
    try:
        subscription_key = AZURE_SPEECH_KEY
        region = AZURE_SPEECH_REGION

        if not subscription_key or not region:
            return jsonify({"error": "Speech key or region not set"}), 500

        # STSトークン発行エンドポイント
        # https://<region>.api.cognitive.microsoft.com/sts/v1.0/issuetoken
        token_url = f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issuetoken"

        headers = {
            "Ocp-Apim-Subscription-Key": subscription_key,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # Token取得(POST)
        resp = requests.post(token_url, headers=headers)
        if resp.status_code != 200:
            return jsonify({"error": f"Failed to get token: {resp.text}"}), 500

        token = resp.text  # 応答ボディがトークン文字列

        return jsonify({"token": token, "region": region})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/chat", methods=["POST"])
def chat():
    """
    ユーザーからのメッセージと会話履歴を受け取り、OpenAIのAPIを使用してAIの応答を返すエンドポイント。
    """
    # OpenAIの設定
    openai.api_key = env_production.get_env_variable("OPENAI_API_KEY")
    try:
        data = request.get_json()
        if not data or 'conversation' not in data:
            return jsonify({'error': 'No conversation provided'}), 400

        conversation = data['conversation']
        if not isinstance(conversation, list):
            return jsonify({'error': 'Conversation should be a list'}), 400

        # システムメッセージを先頭に追加
        messages = [
            {"role": "system", "content": "あなたは役立つAIアシスタントです。"}
        ]

        messages.extend(conversation)  # 会話履歴を追加

        # OpenAI GPT-4との対話
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=300
        )
        ai_text = response['choices'][0]['message']['content'].strip()
        return jsonify({'ai': ai_text})

    except Exception as e:
        return jsonify({'error': 'サーバー内部でエラーが発生しました。'}), 500

if __name__ == "__main__":
    # ローカルデバッグ用
    app.run(debug=True, host="0.0.0.0", port=5000)
