#!/usr/bin/env python3
"""
ElevenLabs STT 세션 연결 테스트
WebSocket 연결 후 session_started 메시지를 받는지 확인
"""
import asyncio
import json
import os
import sys
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


async def test_elevenlabs_session():
    """ElevenLabs STT 세션 연결 테스트"""
    
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
                        logger.info(f"📨 Full message: {json.dumps(data, indent=2)}")
                        
                        if message_type == "session_started":
                            logger.info("✅ Session started successfully!")
                            session_config = data.get("session", {})
                            logger.info(f"📋 Session config: {json.dumps(session_config, indent=2)}")
                            return True  # 세션 시작 확인
                        
                        elif message_type == "input_error":
                            error = data.get("error", "Unknown error")
                            logger.error(f"❌ Input error: {error}")
                            logger.error(f"❌ This means we sent an invalid message before session started")
                            return False
                        
                        elif message_type in ["error", "auth_error", "quota_exceeded"]:
                            error = data.get("error", {})
                            if isinstance(error, dict):
                                error_message = error.get("message", "Unknown error")
                            else:
                                error_message = str(error)
                            logger.error(f"❌ Error ({message_type}): {error_message}")
                            return False
                        
                        else:
                            logger.warning(f"⚠️ Unexpected message type: {message_type}")
                            # 계속 수신 (다른 메시지가 올 수 있음)
                    
                    except json.JSONDecodeError as e:
                        logger.warning(f"⚠️ Invalid JSON: {message[:100]}")
                        logger.warning(f"⚠️ Error: {e}")
                    
                    except Exception as e:
                        logger.error(f"❌ Error processing message: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                
                return False  # 연결 종료
            
            try:
                # 타임아웃과 메시지 수신 중 먼저 완료되는 것 선택
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
                for task in done:
                    result = await task
                    if result is True:
                        session_started = True
                    elif result is False and task.get_name() == "wait_for_timeout":
                        logger.error(f"❌ Timeout: No session_started message received within {timeout} seconds")
                        logger.error(f"📊 Total messages received: {len(messages_received)}")
                        for i, msg in enumerate(messages_received):
                            logger.error(f"📨 Message {i+1}: {json.dumps(msg, indent=2)}")
            
            except Exception as e:
                logger.error(f"❌ Error in message loop: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            if session_started:
                logger.info("✅ Test PASSED: Session started successfully")
                return True
            else:
                logger.error("❌ Test FAILED: Session did not start")
                logger.error(f"📊 Messages received: {len(messages_received)}")
                return False
    
    except websockets.exceptions.InvalidStatusCode as e:
        logger.error(f"❌ WebSocket connection error: HTTP {e.status_code}")
        if e.status_code == 403:
            logger.error("💡 HTTP 403: Authentication failed")
            logger.error("💡 Check if API key is correct and has access to Scribe Realtime v2")
        elif e.status_code == 401:
            logger.error("💡 HTTP 401: Unauthorized")
            logger.error("💡 API key is invalid or expired")
        return False
    
    except Exception as e:
        logger.error(f"❌ Connection error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def main():
    """메인 함수"""
    logger.info("🧪 Starting ElevenLabs STT Session Test")
    logger.info("=" * 60)
    
    success = await test_elevenlabs_session()
    
    logger.info("=" * 60)
    if success:
        logger.info("✅ Test completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Test failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

