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
    return send_from_directory("templates", "index.html")

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
    ユーザーからのテキストを受け取り、OpenAIのAPIを使用してAIの応答を返すエンドポイント。
    """
    # OpenAIの設定
    openai.api_key = env_production.get_env_variable("OPENAI_API_KEY")
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'No message provided'}), 400

        user_message = data['message']
        print(f"User message: {user_message}")

        # OpenAI GPT-4との対話
        print(openai.api_key)
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは役立つAIアシスタントです。"},
                {"role": "user", "content": user_message}
                # {"role": "user", "content": "こんにちは"}
            ],
            max_tokens=150
        )
        ai_text = response['choices'][0]['message']['content'].strip()
        print(f"AI response: {ai_text}") 

        return jsonify({'user': user_message, 'ai': ai_text})

    except Exception as e:
        return jsonify({'error': 'サーバー内部でエラーが発生しました。'}), 500

if __name__ == "__main__":
    # ローカルデバッグ用
    app.run(debug=True, host="0.0.0.0", port=5000)


# from flask import Flask, request, jsonify, render_template
# import azure.cognitiveservices.speech as speechsdk
# import openai
# import os
# import uuid
# import tempfile  # 追加
# import env_production

# app = Flask(__name__)

# # 環境変数からAPIキーとリージョンを取得
# AZURE_SPEECH_KEY = env_production.get_env_variable("AZURE_SPEECH_KEY")
# AZURE_SERVICE_REGION = env_production.get_env_variable("AZURE_SPEECH_REGION")
# # OPENAI_API_KEY = env_production.get_env_variable("OPENAI_API_KEY")

# # OpenAIの設定
# # openai.api_key = OPENAI_API_KEY

# # 音声認識の設定
# speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SERVICE_REGION)

# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/api/chat', methods=['POST'])
# def chat():
#     if 'audio' not in request.files:
#         return jsonify({'error': 'No audio file provided'}), 400

#     audio_file = request.files['audio']
#     audio_filename = f"temp_{uuid.uuid4()}.wav"
#     # 修正箇所: 一時ディレクトリをOSに依存せず取得
#     audio_path = os.path.join(tempfile.gettempdir(), audio_filename)
#     audio_file.save(audio_path)

#     # 音声ファイルをテキストに変換
#     audio_input = speechsdk.AudioConfig(filename=audio_path)
#     speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)

#     result = speech_recognizer.recognize_once()

#     # 一時ファイルの削除
#     os.remove(audio_path)

#     if result.reason != speechsdk.ResultReason.RecognizedSpeech:
#         return jsonify({'error': '音声が認識されませんでした。'}), 400

#     user_text = result.text

#     # OpenAI GPT-4との対話
#     try:
#         response = "AIとの対話は未実装です。"
#         # response = openai.ChatCompletion.create(
#         #     model="gpt-4",
#         #     messages=[
#         #         {"role": "system", "content": "あなたは役立つAIアシスタントです。"},
#         #         {"role": "user", "content": user_text}
#         #     ],
#         #     max_tokens=150
#         # )
#         # ai_text = response['choices'][0]['message']['content'].strip()
#     except Exception as e:
#         return jsonify({'error': 'AIとの対話中にエラーが発生しました。'}), 500

#     return jsonify({'user': user_text, 'ai': ai_text})

# if __name__ == '__main__':
#     app.run(debug=True)
