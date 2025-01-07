# # ws_tts.py

# import asyncio
# import websockets
# import azure.cognitiveservices.speech as speechsdk
# import os
# from dotenv import load_dotenv
# import logging

# load_dotenv()

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
# AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

# async def tts_handler(websocket):
#     """
#     クライアントからテキストを受け取り、Azure Speech SDK (PullAudioOutputStream)で音声を逐次生成し、
#     WebSocketでバイナリ送信する。
#     """
#     try:
#         # 1. クライアントからテキスト受信
#         text = await websocket.recv()  # テキスト(文字列)

#         logger.info(f"Received text for TTS: {text}")

#         # 2. PullAudioOutputStreamの用意
#         pull_stream = speechsdk.audio.PullAudioOutputStream()
#         audio_config = speechsdk.audio.AudioConfig(stream=pull_stream)

#         speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
#         speech_config.speech_synthesis_language = "ja-JP"
#         speech_config.speech_synthesis_voice_name = "ja-JP-NanamiNeural"

#         synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

#         # 3. 合成開始（非同期）
#         result_future = synthesizer.speak_text_async(text)

#         # 4. PullAudioOutputStreamを読み出し (4096バイトずつ)
#         buffer_size = 4096

#         async def read_and_send():
#             while True:
#                 chunk = pull_stream.read(buffer_size)
#                 if not chunk or len(chunk) == 0:
#                     break
#                 await websocket.send(chunk)

#         import asyncio
#         read_task = asyncio.create_task(read_and_send())

#         # 5. 合成完了待ち
#         synth_result = await asyncio.wrap_future(result_future)
#         await read_task

#         if synth_result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
#             logger.error(f"Speech synthesis not completed. Reason: {synth_result.reason}")

#     except Exception as e:
#         logger.exception("Error in tts_handler")
#     finally:
#         await websocket.close()

# async def main():
#     async with websockets.serve(tts_handler, "0.0.0.0", 8765):
#         logger.info("WebSocket TTS server started on ws://0.0.0.0:8765")
#         await asyncio.Future()  # keep running

# if __name__ == "__main__":
#     asyncio.run(main())
