import os
import subprocess
import tempfile
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
import threading
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# .env 파일 로드
load_dotenv()
SPEECH_SERVICE_ENDPOINT = os.getenv("SPEECH_SERVICE_ENDPOINT")
SPEECH_SERVICE_KEY      = os.getenv("SPEECH_SERVICE_KEY")
SPEECH_REGION           = os.getenv("SPEECH_REGION")

# Azure Speech SDK가 지원하는 오디오 형식들
SUPPORTED_FORMATS = {'.wav', '.mp3', '.ogg', '.flac', '.m4a', '.aac'}
# 브라우저에서 녹음되는 형식들 (변환이 필요한 형식)
BROWSER_FORMATS = {'.webm', '.mp4'}

def check_ffmpeg():
    """FFmpeg 설치 여부 확인"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def convert_audio_to_wav(input_path: str) -> str:
    """오디오 파일을 WAV 형식으로 변환"""
    if not check_ffmpeg():
        raise RuntimeError("FFmpeg is not installed. Please install FFmpeg to convert audio files.")
    
    # 임시 WAV 파일 생성
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
        output_path = temp_wav.name
    
    try:
        # FFmpeg를 사용하여 변환
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            '-ar', '16000',          # 16kHz 샘플링 레이트
            '-ac', '1',              # 모노 채널
            '-y',                    # 기존 파일 덮어쓰기
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg conversion failed: {result.stderr}")
            raise RuntimeError(f"Audio conversion failed: {result.stderr}")
        
        logger.info(f"Successfully converted {input_path} to {output_path}")
        return output_path
        
    except Exception as e:
        # 실패 시 임시 파일 삭제
        if os.path.exists(output_path):
            os.unlink(output_path)
        raise e

def transcribe_audio(filepath: str, key: str, region: str):
    logger.info(f"Starting transcription for file: {filepath}")
    
    # 파일 존재 확인
    if not os.path.exists(filepath):
        logger.error(f"Audio file not found: {filepath}")
        raise FileNotFoundError(f"Audio file not found: {filepath}")
    
    # 확장자 검사
    ext = '.' + filepath.rsplit('.', 1)[-1].lower()
    
    # 변환이 필요한 파일인지 확인
    converted_file = None
    working_file = filepath
    
    if ext in BROWSER_FORMATS:
        logger.info(f"Converting {ext} file to WAV format")
        try:
            converted_file = convert_audio_to_wav(filepath)
            working_file = converted_file
            ext = '.wav'
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            raise ValueError(f"Failed to convert audio format {ext}: {str(e)}")
    
    # 지원되지 않는 형식 체크
    if ext not in SUPPORTED_FORMATS:
        logger.error(f"Unsupported audio format: {ext}")
        raise ValueError(f"Unsupported audio format: {ext}. Supported formats: {', '.join(SUPPORTED_FORMATS)}")
    
    try:
        # Azure Speech SDK 설정
        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        # 한국어와 영어 자동 감지
        auto_detect = speechsdk.AutoDetectSourceLanguageConfig(languages=["ko-KR", "en-US"])
        audio_config = speechsdk.AudioConfig(filename=working_file)
        
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            auto_detect_source_language_config=auto_detect,
            audio_config=audio_config
        )
        
        all_results = []
        detected_lang = None
        done = threading.Event()
        error_occurred = None
        
        def handle_final(evt):
            nonlocal detected_lang
            logger.info(f"Recognition result: {evt.result.text}")
            
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                if detected_lang is None:
                    detected_lang = evt.result.properties.get(
                        speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult,
                        "unknown"
                    )
                all_results.append(evt.result.text)
            elif evt.result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning("No speech could be recognized")
        
        def handle_stop(evt):
            logger.info("Recognition session stopped")
            done.set()
        
        def handle_cancel(evt):
            nonlocal error_occurred
            logger.error(f"Recognition canceled: {evt}")
            if evt.reason == speechsdk.CancellationReason.Error:
                error_occurred = f"Speech recognition error: {evt.error_details}"
            done.set()
        
        # 이벤트 핸들러 연결
        recognizer.recognized.connect(handle_final)
        recognizer.session_stopped.connect(handle_stop)
        recognizer.canceled.connect(handle_cancel)
        
        # 연속 인식 시작
        logger.info("Starting continuous recognition...")
        recognizer.start_continuous_recognition()
        
        # 완료까지 대기 (최대 30초 타임아웃 추가)
        if not done.wait(timeout=30):
            logger.warning("Recognition timed out")
            recognizer.stop_continuous_recognition()
            raise TimeoutError("Speech recognition timed out")
        
        recognizer.stop_continuous_recognition()
        
        # 에러가 발생했다면 예외 발생
        if error_occurred:
            raise Exception(error_occurred)
        
        final_text = ' '.join(all_results).strip()
        logger.info(f"Final transcription: {final_text}")
        
        return {
            "detected_language": detected_lang or "unknown",
            "transcription": final_text
        }
    
    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        raise
    
    finally:
        # 변환된 임시 파일 삭제
        if converted_file and os.path.exists(converted_file):
            try:
                os.unlink(converted_file)
                logger.info(f"Cleaned up converted file: {converted_file}")
            except Exception as e:
                logger.warning(f"Failed to clean up converted file: {e}")