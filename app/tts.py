# app/tts.py

import os
import uuid
import requests
from dotenv import load_dotenv

# .env 로드
load_dotenv()

# 환경변수로부터 엔드포인트와 키 가져오기
lan_endpoint = os.getenv("LAN_ENDPOINT")
lan_key = os.getenv("LAN_KEY")
tts_endpoint = os.getenv("TTS_ENDPOINT")
tts_key = os.getenv("TTS_KEY")

# 언어 코드별 음성 매핑
voice_mapping = {
    'en': 'en-US-JennyNeural',
    'ko': 'ko-KR-GookMinNeural',
    'ja': 'ja-JP-NanamiNeural',
    'zh': 'zh-CN-XiaoxiaoNeural',
    'fr': 'fr-FR-DeniseNeural',
    'de': 'de-DE-KatjaNeural',
    'es': 'es-ES-ElviraNeural'
}

def lan_det(text: str) -> str:
    """
    Azure Language Service를 호출하여 텍스트의 언어 코드를 반환합니다.
    실패 시 None을 반환합니다.
    """
    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": lan_key
    }
    body = {
        "kind": "LanguageDetection",
        "parameters": {"modelVersion": "latest"},
        "analysisInput": {
            "documents": [
                {"id": "1", "text": text}
            ]
        }
    }
    response = requests.post(lan_endpoint, headers=headers, json=body)
    if response.status_code == 200:
        return response.json()['results']['documents'][0]['detectedLanguage']['iso6391Name']
    else:
        # 실패 시 None 반환
        print("Language detection failed:", response.status_code, response.text)
        return None

def request_tts(text: str, lang_code: str) -> bytes | None:
    """
    Azure TTS를 호출하여 음성(바이너리: mp3)을 바로 반환합니다.
    - text: 읽어줄 문자열
    - lang_code: ISO-639-1 언어 코드 (예: 'ko', 'en')
    성공 시 mp3 데이터(bytes)를 반환하고, 실패 시 None을 반환합니다.
    """
    headers = {
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
        "Ocp-Apim-Subscription-Key": tts_key
    }

    # 해당 언어코드에 매핑된 음성 이름을 찾고, 없으면 en-US-JennyNeural 사용
    voice_name = voice_mapping.get(lang_code, "en-US-JennyNeural")

    # SSML 본문 생성
    ssml = f"""
    <speak version='1.0' xml:lang='{lang_code}'>
        <voice xml:lang='{lang_code}' xml:gender='Female' name='{voice_name}'>
            <prosody rate="0%">
                {text}
            </prosody>
        </voice>
    </speak>
    """

    response = requests.post(tts_endpoint, headers=headers, data=ssml.encode("utf-8"))
    if response.status_code == 200:
        # mp3 바이너리를 그대로 반환
        return response.content
    else:
        print("TTS failed:", response.status_code, response.text)
        return None
