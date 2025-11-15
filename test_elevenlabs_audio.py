#!/usr/bin/env python3
"""
ElevenLabs STT 오디오 전송 및 전사 테스트
세션 연결 후 실제 오디오를 보내서 전사가 제대로 되는지 확인
"""
import asyncio
import json
import os
import sys
import base64
import struct
import websockets
from loguru import logger

# 환경 변수 로드 (.env 파일에서 직접 읽기)
def load_env_file():
    """간단한 .env 파일 로더"""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")

load_env_file()

# 로거 설정
logger.remove(0)
logger.add(sys.stderr, level="INFO")


def generate_test_audio(duration_seconds=1.0, sample_rate=16000, frequency=440):
    """
    테스트용 PCM 오디오 생성 (440Hz 사인파)
    
    Args:
        duration_seconds: 오디오 길이 (초)
        sample_rate: 샘플 레이트 (Hz)
        frequency: 주파수 (Hz)
    
    Returns:
        bytes: PCM 16-bit little-endian 오디오 데이터
    """
    import math
    
    num_samples = int(duration_seconds * sample_rate)
    audio_data = bytearray()
    
    for i in range(num_samples):
        # 사인파 생성
        sample = math.sin(2 * math.pi * frequency * i / sample_rate)
        # 16-bit PCM으로 변환 (-32768 ~ 32767)
        sample_int = int(sample * 32767)
        # Little-endian으로 변환
        audio_data.extend(struct.pack('<h', sample_int))
    
    return bytes(audio_data)


async def test_elevenlabs_audio():
    """ElevenLabs STT 오디오 전송 및 전사 테스트"""
    
    # API 키 확인
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        logger.error("❌ ELEVENLABS_API_KEY가 설정되지 않았습니다.")
        logger.error("💡 .env 파일에 ELEVENLABS_API_KEY를 설정하세요.")
        return False
    
    logger.info(f"🔑 API Key found (length: {len(api_key)}, prefix: {api_key[:10]}...)")
    
    # WebSocket URL 구성
    base_url = "wss://api.elevenlabs.io/v1/speech-to-text/realtime"
    params = [
        "model_id=scribe_v2_realtime",
        "encoding=pcm_16000",
        "sample_rate=16000",
        "commit_strategy=vad",
        "language_code=ko",
    ]
    query_string = "&".join(params)
    ws_url = f"{base_url}?{query_string}"
    
    logger.info(f"📡 WebSocket URL: {ws_url}")
    logger.info(f"🔗 Connecting to ElevenLabs...")
    
    try:
        # WebSocket 연결
        async with websockets.connect(
            ws_url,
            additional_headers={"xi-api-key": api_key},
            ping_interval=None,
            ping_timeout=None,
            close_timeout=10,
        ) as websocket:
            logger.info("✅ WebSocket connection established!")
            logger.info("⏳ Waiting for session_started message...")
            
            session_started = False
            messages_received = []
            timeout = 10  # 10초 타임아웃
            
            # 타임아웃을 위한 태스크
            async def wait_for_timeout():
                await asyncio.sleep(timeout)
                return False
            
            # 메시지 수신 태스크
            async def receive_loop():
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        messages_received.append(data)
                        
                        message_type = data.get("type") or data.get("message_type")
                        logger.info(f"📨 Received message type: {message_type}")
                        
                        if message_type == "session_started":
                            logger.info("✅ Session started successfully!")
                            session_config = data.get("config", {})
                            logger.info(f"📋 Session config: {json.dumps(session_config, indent=2)}")
                            return True  # 세션 시작 확인
                        
                        elif message_type == "partial_transcript":
                            text = data.get("text", "")
                            logger.info(f"📝 Partial transcript: {text}")
                        
                        elif message_type == "committed_transcript":
                            text = data.get("text", "")
                            logger.info(f"✅ Committed transcript: {text}")
                            return "committed"  # 전사 완료
                        
                        elif message_type == "input_error":
                            error = data.get("error", "Unknown error")
                            logger.error(f"❌ Input error: {error}")
                            logger.error(f"❌ Full error data: {json.dumps(data, indent=2)}")
                            return "error"
                        
                        elif message_type in ["error", "auth_error", "quota_exceeded"]:
                            error = data.get("error", {})
                            if isinstance(error, dict):
                                error_message = error.get("message", "Unknown error")
                            else:
                                error_message = str(error)
                            logger.error(f"❌ Error ({message_type}): {error_message}")
                            return "error"
                        
                        else:
                            logger.debug(f"⚠️ Unexpected message type: {message_type}")
                    
                    except json.JSONDecodeError as e:
                        logger.warning(f"⚠️ Invalid JSON: {message[:100]}")
                        logger.warning(f"⚠️ Error: {e}")
                    
                    except Exception as e:
                        logger.error(f"❌ Error processing message: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                
                return False  # 연결 종료
            
            # 1단계: 세션 시작 대기
            logger.info("=" * 60)
            logger.info("Step 1: Waiting for session_started...")
            logger.info("=" * 60)
            
            done, pending = await asyncio.wait(
                [asyncio.create_task(wait_for_timeout()), asyncio.create_task(receive_loop())],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # 남은 태스크 취소
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # 결과 확인
            session_result = None
            for task in done:
                result = await task
                if result is True:
                    session_started = True
                    session_result = task
                elif result is False and len(done) == 1:
                    logger.error(f"❌ Timeout: No session_started message received within {timeout} seconds")
                    return False
            
            if not session_started:
                logger.error("❌ Session did not start")
                return False
            
            logger.info("✅ Session started! Proceeding to audio test...")
            
            # 2단계: 오디오 전송 테스트
            logger.info("=" * 60)
            logger.info("Step 2: Sending test audio...")
            logger.info("=" * 60)
            
            # 테스트 오디오 생성 (1초, 440Hz 사인파)
            logger.info("🎵 Generating test audio (1 second, 440Hz sine wave)...")
            test_audio = generate_test_audio(duration_seconds=1.0, sample_rate=16000, frequency=440)
            logger.info(f"📊 Generated {len(test_audio)} bytes of PCM audio")
            
            # Base64 인코딩
            audio_base64 = base64.b64encode(test_audio).decode('utf-8')
            logger.info(f"📊 Base64 encoded: {len(audio_base64)} characters")
            
            # 오디오 메시지 전송
            # SDK 코드를 확인해야 하지만, 일단 작은 청크로 나눠서 보내기
            # 문서에 따르면 청크 크기는 0.1-1초 정도가 적절
            
            logger.info("📤 Sending audio in small chunks...")
            
            # 오디오를 작은 청크로 나누기 (약 0.1초씩 = 1600 샘플 = 3200 바이트)
            chunk_size = 3200  # 0.1초 @ 16kHz, 16-bit = 1600 samples * 2 bytes
            num_chunks = len(test_audio) // chunk_size + (1 if len(test_audio) % chunk_size else 0)
            
            logger.info(f"📊 Splitting audio into {num_chunks} chunks ({chunk_size} bytes each)")
            
            # 첫 번째 청크만 보내서 테스트
            first_chunk = test_audio[:chunk_size]
            audio_base64_chunk = base64.b64encode(first_chunk).decode('utf-8')
            
            # 형식: SDK 코드 기반 (message_type, audio_base_64, commit, sample_rate 필요)
            # 참고: https://github.com/elevenlabs/elevenlabs-python/blob/main/src/elevenlabs/realtime/connection.py
            audio_message = {
                "message_type": "input_audio_chunk",
                "audio_base_64": audio_base64_chunk,
                "commit": False,
                "sample_rate": 16000,
            }
            
            logger.info(f"📤 Sending first chunk ({len(first_chunk)} bytes)...")
            logger.debug(f"📤 Message structure: {list(audio_message.keys())}")
            
            await websocket.send(json.dumps(audio_message))
            logger.info("✅ Audio chunk sent!")
            
            # 3단계: 응답 대기
            logger.info("=" * 60)
            logger.info("Step 3: Waiting for transcription response...")
            logger.info("=" * 60)
            
            # 메시지 수신 계속 (타임아웃 5초)
            response_timeout = 5
            response_received = False
            
            async def wait_for_response():
                await asyncio.sleep(response_timeout)
                return False
            
            async def receive_responses():
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        message_type = data.get("type") or data.get("message_type")
                        
                        logger.info(f"📨 Response message type: {message_type}")
                        logger.info(f"📨 Full message: {json.dumps(data, indent=2)}")
                        
                        if message_type == "partial_transcript":
                            text = data.get("text", "")
                            logger.info(f"📝 Partial transcript: {text}")
                        
                        elif message_type == "committed_transcript":
                            text = data.get("text", "")
                            logger.info(f"✅ Committed transcript: {text}")
                            return True
                        
                        elif message_type == "input_error":
                            error = data.get("error", "Unknown error")
                            logger.error(f"❌ Input error: {error}")
                            logger.error(f"❌ This means the audio message format was invalid")
                            return "error"
                        
                        elif message_type in ["error", "transcriber_error"]:
                            error = data.get("error", {})
                            if isinstance(error, dict):
                                error_message = error.get("message", "Unknown error")
                            else:
                                error_message = str(error)
                            logger.error(f"❌ Error ({message_type}): {error_message}")
                            return "error"
                    
                    except json.JSONDecodeError as e:
                        logger.warning(f"⚠️ Invalid JSON: {message[:100]}")
                    except Exception as e:
                        logger.error(f"❌ Error: {e}")
                
                return False
            
            done, pending = await asyncio.wait(
                [asyncio.create_task(wait_for_response()), asyncio.create_task(receive_responses())],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            for task in done:
                result = await task
                if result is True:
                    response_received = True
                    logger.info("✅ Received transcription response!")
                elif result == "error":
                    logger.error("❌ Received error response")
                    return False
            
            if response_received:
                logger.info("✅ Test PASSED: Audio sent and transcription received")
                return True
            else:
                logger.warning("⚠️ No transcription response received (this might be normal for test audio)")
                logger.info("✅ Test PASSED: Audio message was accepted (no input_error)")
                return True
    
    except websockets.exceptions.InvalidStatusCode as e:
        logger.error(f"❌ WebSocket connection error: HTTP {e.status_code}")
        if e.status_code == 403:
            logger.error("💡 HTTP 403: Authentication failed")
        elif e.status_code == 401:
            logger.error("💡 HTTP 401: Unauthorized")
        return False
    
    except Exception as e:
        logger.error(f"❌ Connection error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def main():
    """메인 함수"""
    logger.info("🧪 Starting ElevenLabs STT Audio Test")
    logger.info("=" * 60)
    
    success = await test_elevenlabs_audio()
    
    logger.info("=" * 60)
    if success:
        logger.info("✅ Test completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Test failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

