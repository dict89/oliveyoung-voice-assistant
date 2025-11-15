"""
ElevenLabs Scribe Realtime v2 STT 서비스
Pipecat 프레임 시스템과 통합

참고: ElevenLabs Python SDK 소스 코드 기반
https://github.com/elevenlabs/elevenlabs-python/blob/main/src/elevenlabs/realtime/scribe.py
https://elevenlabs.io/docs/cookbooks/speech-to-text/streaming
"""
import asyncio
import base64
import json
from typing import Optional

import websockets
from loguru import logger
from pipecat.frames.frames import AudioRawFrame, TranscriptionFrame, Frame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class CommitStrategy:
    """전사 커밋 전략"""
    VAD = "vad"  # Voice Activity Detection - 자동 커밋
    MANUAL = "manual"  # 수동 커밋


class ElevenLabsSTTService(FrameProcessor):
    """ElevenLabs Scribe Realtime v2 STT 서비스
    
    공식 SDK와 동일한 방식으로 구현:
    - API 키를 xi-api-key 헤더로 전달
    - WebSocket URL: wss://api.elevenlabs.io/v1/speech-to-text/realtime
    - 쿼리 파라미터: model_id, encoding, sample_rate, commit_strategy, language_code
    """
    
    def __init__(
        self,
        api_key: str,  # ElevenLabs API 키 (Single-use token 불필요)
        model_id: str = "scribe_v2_realtime",
        sample_rate: int = 16000,
        language_code: Optional[str] = None,  # ISO-639-1 또는 ISO-639-3 (예: "ko", "en")
        commit_strategy: str = CommitStrategy.VAD,  # VAD 또는 MANUAL
    ):
        super().__init__()
        self.api_key = api_key
        self.model_id = model_id
        self.sample_rate = sample_rate
        self.language_code = language_code
        self.commit_strategy = commit_strategy
        
        # WebSocket 연결
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connection_task: Optional[asyncio.Task] = None
        self.is_connected = False
        self.session_started = False  # 세션 시작 여부
        
        # 오디오 형식 (PCM)
        # sample_rate에 따라 encoding 결정
        self.encoding = f"pcm_{sample_rate}"
        
        # 부분 전사 결과
        self.partial_transcript = ""
        self.last_committed_transcript = ""
        
        # 재연결 관련
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        
        # 오디오 통계 (디버깅용)
        self.audio_chunks_sent = 0
        self.audio_bytes_sent = 0
    
    def _build_websocket_url(self) -> str:
        """WebSocket URL 구성 (SDK와 동일한 방식)"""
        base_url = "wss://api.elevenlabs.io/v1/speech-to-text/realtime"
        
        # 쿼리 파라미터 구성
        params = [
            f"model_id={self.model_id}",
            f"encoding={self.encoding}",
            f"sample_rate={self.sample_rate}",
            f"commit_strategy={self.commit_strategy}",
        ]
        
        # 언어 코드 추가 (있는 경우)
        if self.language_code:
            params.append(f"language_code={self.language_code}")
        
        query_string = "&".join(params)
        return f"{base_url}?{query_string}"
    
    async def _connect(self):
        """ElevenLabs WebSocket에 연결"""
        try:
            # API 키 검증
            if not self.api_key or len(self.api_key) < 10:
                raise ValueError(f"Invalid API key: key length is {len(self.api_key) if self.api_key else 0}")
            
            logger.info(f"🔌 Connecting to ElevenLabs WebSocket...")
            logger.info(f"📝 API key length: {len(self.api_key)}")
            logger.info(f"📝 API key prefix: {self.api_key[:10]}...")
            logger.info(f"📝 Model: {self.model_id}")
            logger.info(f"📝 Sample rate: {self.sample_rate}")
            logger.info(f"📝 Encoding: {self.encoding}")
            logger.info(f"📝 Commit strategy: {self.commit_strategy}")
            logger.info(f"📝 Language: {self.language_code or 'auto'}")
            
            # WebSocket URL 구성
            ws_url = self._build_websocket_url()
            logger.info(f"📡 WebSocket URL: {ws_url}")
            
            # WebSocket 연결 (xi-api-key 헤더로 인증)
            logger.info(f"🔗 Attempting WebSocket connection to ElevenLabs...")
            
            self.websocket = await websockets.connect(
                ws_url,
                additional_headers={"xi-api-key": self.api_key},
                ping_interval=None,
                ping_timeout=None,
                close_timeout=10,
            )
            
            logger.info(f"✅ WebSocket connection established!")
            
            self.is_connected = True
            self.reconnect_attempts = 0
            
            # 메시지 수신 태스크 시작
            self.connection_task = asyncio.create_task(self._receive_messages())
            
            logger.info(f"✅ ElevenLabs STT connected (model: {self.model_id}, sample_rate: {self.sample_rate}, language: {self.language_code or 'auto'})")
            logger.info(f"⏳ Waiting for session_started message...")
            
        except websockets.exceptions.InvalidStatusCode as e:
            logger.error(f"❌ ElevenLabs STT connection error: HTTP {e.status_code}")
            
            # HTTP 응답 본문 읽기 시도
            try:
                if hasattr(e, 'response') and e.response:
                    response_body = await e.response.text()
                    logger.error(f"❌ Response body: {response_body}")
            except:
                pass
            
            if e.status_code == 403:
                logger.error(f"💡 HTTP 403: Authentication failed")
                logger.error(f"💡 Possible causes:")
                logger.error(f"💡   1. API key is invalid or expired")
                logger.error(f"💡   2. API key does not have access to Scribe Realtime v2")
                logger.error(f"💡   3. Scribe Realtime v2 requires a paid plan")
                logger.error(f"💡   4. WebSocket URL format may be incorrect")
                logger.error(f"💡 Solutions:")
                logger.error(f"💡   - Check if ELEVENLABS_API_KEY is correct in .env file")
                logger.error(f"💡   - Verify your ElevenLabs account has access to Scribe Realtime v2")
                logger.error(f"💡   - Check if your plan includes Scribe Realtime v2")
            elif e.status_code == 401:
                logger.error(f"💡 HTTP 401: Unauthorized")
                logger.error(f"💡 API key is invalid or expired")
                logger.error(f"💡 Check if ELEVENLABS_API_KEY is correct in .env file")
            elif e.status_code == 404:
                logger.error(f"💡 HTTP 404: WebSocket endpoint not found")
                logger.error(f"💡 Check if WebSocket URL is correct")
                logger.error(f"💡 URL: {ws_url}")
            else:
                logger.error(f"💡 HTTP {e.status_code}: Unexpected error")
                logger.error(f"💡 Check ElevenLabs API status and documentation")
            
            self.is_connected = False
            raise
        except Exception as e:
            logger.error(f"❌ ElevenLabs STT connection error: {e}")
            logger.error(f"💡 Error type: {type(e).__name__}")
            logger.error(f"💡 Error details: {str(e)}")
            logger.error(f"💡 API key length: {len(self.api_key) if self.api_key else 0}")
            logger.error(f"💡 Check if ELEVENLABS_API_KEY is correct in .env file")
            self.is_connected = False
            raise
    
    async def _receive_messages(self):
        """WebSocket 메시지 수신 루프"""
        try:
            logger.info("📡 Starting message receiver loop...")
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ Invalid JSON received: {message[:100]}")
                    logger.warning(f"⚠️ JSON error: {e}")
                except Exception as e:
                    logger.error(f"❌ Error handling message: {e}")
                    logger.error(f"❌ Error type: {type(e).__name__}")
                    import traceback
                    logger.error(f"❌ Traceback: {traceback.format_exc()}")
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"⚠️ ElevenLabs WebSocket connection closed: {e}")
            self.is_connected = False
            self.session_started = False
        except Exception as e:
            logger.error(f"❌ Error receiving messages: {e}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            self.is_connected = False
            self.session_started = False
    
    async def _handle_message(self, data: dict):
        """ElevenLabs 메시지 처리"""
        message_type = data.get("type")
        
        # 모든 메시지 타입 로깅 (디버깅용)
        logger.debug(f"📨 Received message type: {message_type}")
        
        if message_type == "session_started":
            logger.info("✅ ElevenLabs session started")
            self.session_started = True  # 세션 시작 플래그 설정
            # 세션 설정 확인
            session_config = data.get("session", {})
            logger.info(f"📋 Session config: {session_config}")
        
        elif message_type == "partial_transcript":
            # 부분 전사 결과 (실시간 업데이트)
            text = data.get("text", "")
            if text:
                self.partial_transcript = text
                # 부분 전사는 로깅 (INFO 레벨로 변경)
                logger.info(f"📝 Partial transcript: {text}")
        
        elif message_type == "committed_transcript":
            # 확정된 전사 결과 (최종)
            text = data.get("text", "")
            if text and text.strip():
                self.last_committed_transcript = text.strip()
                self.partial_transcript = ""
                
                # TranscriptionFrame 생성 및 전달
                logger.info(f"✅ Committed transcript: {text.strip()}")
                frame = TranscriptionFrame(text=text.strip(), user_id="user")
                await self.push_frame(frame, FrameDirection.DOWNSTREAM)
        
        elif message_type == "committed_transcript_with_timestamps":
            # 타임스탬프 포함 전사 결과
            text = data.get("text", "")
            if text and text.strip():
                self.last_committed_transcript = text.strip()
                self.partial_transcript = ""
                
                # TranscriptionFrame 생성 및 전달
                logger.info(f"✅ Committed transcript (with timestamps): {text.strip()}")
                frame = TranscriptionFrame(text=text.strip(), user_id="user")
                await self.push_frame(frame, FrameDirection.DOWNSTREAM)
        
        elif message_type == "error":
            error = data.get("error", {})
            error_type = error.get("type", "unknown")
            error_message = error.get("message", "Unknown error")
            logger.error(f"❌ ElevenLabs error ({error_type}): {error_message}")
            logger.error(f"❌ Full error data: {data}")
            self.is_connected = False
            self.session_started = False
        
        elif message_type == "auth_error":
            error = data.get("error", {})
            error_message = error.get("message", "Authentication error")
            logger.error(f"❌ ElevenLabs authentication error: {error_message}")
            logger.error(f"❌ Full error data: {data}")
            self.is_connected = False
            self.session_started = False
        
        elif message_type == "quota_exceeded":
            error = data.get("error", {})
            error_message = error.get("message", "Quota exceeded")
            logger.error(f"❌ ElevenLabs quota exceeded: {error_message}")
            logger.error(f"❌ Full error data: {data}")
            self.is_connected = False
            self.session_started = False
        
        elif message_type == "transcriber_error":
            error = data.get("error", {})
            error_message = error.get("message", "Transcriber error")
            logger.error(f"❌ ElevenLabs transcriber error: {error_message}")
            logger.error(f"❌ Full error data: {data}")
        
        elif message_type == "input_error":
            error = data.get("error", {})
            error_message = error.get("message", "Input error")
            logger.error(f"❌ ElevenLabs input error: {error_message}")
            logger.error(f"❌ Full error data: {data}")
        
        else:
            # 알 수 없는 메시지 타입
            logger.warning(f"⚠️ Unknown message type: {message_type}")
            logger.debug(f"⚠️ Full message data: {data}")
    
    async def _send_audio(self, audio_data: bytes):
        """오디오 데이터를 ElevenLabs로 전송
        
        참고: SDK에서는 audio_base_64 필드만 전송 (타입 없이)
        """
        if not self.is_connected or not self.websocket:
            logger.warning("⚠️ Cannot send audio: not connected")
            return
        
        if not self.session_started:
            # 세션이 시작되지 않았으면 오디오 전송하지 않음
            logger.debug("⚠️ Cannot send audio: session not started yet")
            return
        
        try:
            # PCM 오디오를 base64로 인코딩
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # 오디오 청크 전송 (SDK와 동일한 형식)
            # 타입 필드 없이 audio_base_64만 전송
            message = {
                "audio_base_64": audio_base64,
            }
            
            await self.websocket.send(json.dumps(message))
            
            # 통계 업데이트
            self.audio_chunks_sent += 1
            self.audio_bytes_sent += len(audio_data)
            
            # 주기적으로 로깅 (매 100개 청크마다)
            if self.audio_chunks_sent % 100 == 0:
                logger.debug(f"📤 Sent {self.audio_chunks_sent} audio chunks ({self.audio_bytes_sent} bytes total)")
            
        except websockets.exceptions.ConnectionClosed:
            logger.warning("⚠️ ElevenLabs WebSocket connection closed while sending audio")
            self.is_connected = False
            self.session_started = False
        except Exception as e:
            logger.error(f"❌ Error sending audio: {e}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            self.is_connected = False
            self.session_started = False
    
    async def _commit_transcript(self):
        """전사 세그먼트 확정 (수동 커밋, commit_strategy가 MANUAL일 때만 사용)"""
        if not self.is_connected or not self.websocket:
            return
        
        if self.commit_strategy != CommitStrategy.MANUAL:
            return  # VAD 모드에서는 자동 커밋
        
        try:
            # commit 메시지 전송
            message = {
                "type": "commit",
            }
            await self.websocket.send(json.dumps(message))
            logger.debug("📤 Sent commit message to ElevenLabs")
        except Exception as e:
            logger.error(f"❌ Error committing transcript: {e}")
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """프레임 처리 (AudioRawFrame을 받아서 TranscriptionFrame 생성)"""
        await super().process_frame(frame, direction)
        
        # AudioRawFrame 처리
        if isinstance(frame, AudioRawFrame):
            if not self.is_connected:
                # 연결되지 않은 경우 연결 시도
                logger.info("🔌 Not connected, attempting to connect...")
                try:
                    await self._connect()
                    # 세션 시작을 기다림 (최대 5초)
                    max_wait = 50  # 0.1초 * 50 = 5초
                    waited = 0
                    while not self.session_started and waited < max_wait:
                        await asyncio.sleep(0.1)
                        waited += 1
                    
                    if not self.session_started:
                        logger.warning("⚠️ Session not started after 5 seconds, continuing anyway...")
                    else:
                        logger.info("✅ Session started, ready to receive audio")
                except Exception as e:
                    logger.error(f"❌ Failed to connect to ElevenLabs: {e}")
                    return
            
            # 오디오 데이터 전송
            # AudioRawFrame은 audio 속성이 bytes 형식 (PCM 16-bit little-endian)
            audio_data = frame.audio
            
            # audio_data가 bytes인지 확인
            if audio_data is not None:
                audio_bytes = None
                
                if isinstance(audio_data, bytes):
                    audio_bytes = audio_data
                elif isinstance(audio_data, bytearray):
                    audio_bytes = bytes(audio_data)
                else:
                    # 예상치 못한 형식인 경우 로깅
                    logger.warning(f"⚠️ Unexpected audio format: {type(audio_data)}")
                    return
                
                # 오디오 데이터 전송 (빈 데이터는 건너뜀)
                if audio_bytes and len(audio_bytes) > 0:
                    # 처음 몇 개 프레임만 로깅
                    if self.audio_chunks_sent < 5:
                        logger.debug(f"🎵 Sending audio chunk {self.audio_chunks_sent + 1}: {len(audio_bytes)} bytes")
                    await self._send_audio(audio_bytes)
            else:
                logger.warning("⚠️ AudioRawFrame has no audio data")
        
        # 다른 프레임은 그대로 전달
        else:
            await self.push_frame(frame, direction)
    
    async def cleanup(self):
        """정리 작업"""
        self.is_connected = False
        self.session_started = False
        
        if self.connection_task:
            self.connection_task.cancel()
            try:
                await self.connection_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error(f"❌ Error closing WebSocket: {e}")
        
        logger.info(f"🧹 ElevenLabs STT cleanup completed (sent {self.audio_chunks_sent} chunks, {self.audio_bytes_sent} bytes)")
