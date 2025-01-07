# app.py
import os
import requests
from flask import Flask, jsonify, send_from_directory, request, Response, stream_with_context
import openai
from flask_cors import CORS
import env_production
import azure.cognitiveservices.speech as speechsdk
import logging
import json

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # クロスオリジンリクエストを許可

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数からAPIキーとリージョンを取得
AZURE_SPEECH_KEY = env_production.get_env_variable("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = env_production.get_env_variable("AZURE_SPEECH_REGION")
OPENAI_API_KEY = env_production.get_env_variable("OPENAI_API_KEY")

# OpenAIの設定
openai.api_key = OPENAI_API_KEY

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
            logger.error("Speech key or region not set")
            return jsonify({"error": "Speech key or region not set"}), 500

        # STSトークン発行エンドポイント
        token_url = f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issuetoken"

        headers = {
            "Ocp-Apim-Subscription-Key": subscription_key,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # Token取得(POST)
        resp = requests.post(token_url, headers=headers)
        if resp.status_code != 200:
            logger.error(f"Failed to get token: {resp.text}")
            return jsonify({"error": f"Failed to get token: {resp.text}"}), 500

        token = resp.text  # 応答ボディがトークン文字列

        return jsonify({"token": token, "region": region})

    except Exception as e:
        logger.exception("Exception in /token endpoint")
        return jsonify({"error": str(e)}), 500

@app.route("/api/chat", methods=["POST"])
def chat():
    """
    ユーザーからのメッセージと会話履歴を受け取り、OpenAIのストリーミングAPIを使用してAIの応答をストリーミングで返すエンドポイント。
    """
    def generate():
        try:
            data = request.get_json()
            if not data or 'conversation' not in data:
                logger.error("No conversation provided")
                yield "data: {\"error\": \"No conversation provided\"}\n\n"
                return

            conversation = data['conversation']
            if not isinstance(conversation, list):
                logger.error("Conversation is not a list")
                yield "data: {\"error\": \"Conversation should be a list\"}\n\n"
                return

            # システムメッセージを先頭に追加
            messages = [
                {"role": "system", "content": "あなたは役立つAIアシスタントです。"}
            ]

            messages.extend(conversation)  # 会話履歴を追加

            # OpenAI GPT-4との対話（ストリーミング）
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                max_tokens=300,
                stream=True  # ストリーミングを有効化
            )

            for chunk in response:
                if 'choices' in chunk:
                    delta = chunk['choices'][0]['delta']
                    if 'content' in delta:
                        content = delta['content']
                        # JSON形式で部分的なテキストを送信
                        yield f"data: {json.dumps({'content': content})}\n\n"

            # 最終的なメッセージの送信
            yield f"data: {json.dumps({'content': '【END】'})}\n\n"

        except Exception as e:
            logger.exception("Exception in /api/chat endpoint")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route("/api/tts", methods=["POST"])
def tts():
    """
    AIからの部分的なテキストを受け取り、Azure TextToSpeechで音声化したデータを返すエンドポイント。
    """
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            logger.error("No text provided")
            return jsonify({'error': 'No text provided'}), 400

        text = data['text']
        if not isinstance(text, str):
            logger.error("Text is not a string")
            return jsonify({'error': 'Text should be a string'}), 400

        # 文章の終わりを確認
        if text.strip() == "【END】":
            return jsonify({'status': 'completed'}), 200

        # Azure Speech SDKの設定
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
        speech_config.speech_synthesis_language = "ja-JP"  # 必要に応じて変更
        speech_config.speech_synthesis_voice_name = "ja-JP-NanamiNeural"  # 必要に応じて変更

        # 音声出力形式をMP3に設定
        speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3)

        # SSMLで速度を設定（オプション）
        ssml = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="ja-JP">
            <voice name="{speech_config.speech_synthesis_voice_name}">
                <prosody rate="150%">{text.strip()}</prosody>
            </voice>
        </speak>
        """

        # SpeechSynthesizerを作成（音声出力なし）
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        result = synthesizer.speak_ssml_async(ssml).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            # SpeechSynthesisResultのaudio_dataを取得
            audio_data = result.audio_data  # バイト列として取得

            # 音声データを返却（MIMEタイプをaudio/mpegに変更）
            return Response(audio_data, mimetype="audio/mpeg")

        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            error_message = f"Speech synthesis canceled: {cancellation_details.reason}"
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                error_message += f", {cancellation_details.error_details}"
            logger.error(error_message)
            return jsonify({'error': error_message}), 500

        else:
            logger.error("Speech synthesis failed")
            return jsonify({'error': 'Speech synthesis failed'}), 500

    except Exception as e:
        logger.exception("Exception in /api/tts endpoint")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    # ローカルデバッグ用
    app.run(debug=True, host="0.0.0.0", port=5000)
