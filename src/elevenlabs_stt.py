"""
ElevenLabs Scribe Realtime v2 STT 서비스
Pipecat 프레임 시스템과 통합
"""
import asyncio
import base64
import json
import os
from typing import Optional

import websockets
from loguru import logger
from pipecat.frames.frames import AudioRawFrame, TranscriptionFrame, Frame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class ElevenLabsSTTService(FrameProcessor):
    """ElevenLabs Scribe Realtime v2 STT 서비스"""
    
    def __init__(
        self,
        token: str,  # Single-use token (서버에서 생성)
        model_id: str = "scribe_v2_realtime",
        sample_rate: int = 16000,
        language: Optional[str] = None,
    ):
        super().__init__()
        self.token = token  # Single-use token 사용
        self.model_id = model_id
        self.sample_rate = sample_rate
        self.language = language  # ko/en, None이면 자동 감지
        
        # WebSocket 연결
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connection_task: Optional[asyncio.Task] = None
        self.is_connected = False
        
        # 오디오 버퍼
        self.audio_buffer = bytearray()
        
        # 부분 전사 결과
        self.partial_transcript = ""
        self.last_committed_transcript = ""
        
        # 재연결 관련
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        
    async def _connect(self):
        """ElevenLabs WebSocket에 연결"""
        try:
            # 토큰 검증
            if not self.token or len(self.token) < 10:
                raise ValueError(f"Invalid token: token length is {len(self.token) if self.token else 0}")
            
            logger.info(f"🔌 Connecting to ElevenLabs WebSocket...")
            logger.info(f"📝 Token length: {len(self.token)}")
            logger.info(f"📝 Token prefix: {self.token[:10]}...")
            logger.info(f"📝 Language: {self.language or 'auto'}")
            
            # WebSocket URL 구성
            # ElevenLabs 문서에 따르면: wss://api.elevenlabs.io/v1/speech-to-text/realtime/websocket?token={token}
            # 참고: https://elevenlabs.io/docs/cookbooks/speech-to-text/streaming
            base_url = "wss://api.elevenlabs.io/v1/speech-to-text/realtime/websocket"
            
            # 쿼리 파라미터 구성
            # ElevenLabs 문서에 따르면 토큰을 쿼리 파라미터로 전달
            # 참고: 토큰에 특수 문자가 있을 수 있으므로 URL 인코딩 사용
            from urllib.parse import quote_plus
            
            # 토큰과 언어를 쿼리 파라미터로 구성
            url = f"{base_url}?token={quote_plus(self.token)}"
            if self.language:
                url += f"&language={self.language}"
            
            logger.info(f"📡 WebSocket URL: {base_url}?token=***&language={self.language if self.language else 'none'}")
            logger.debug(f"📡 Token format: {self.token[:30]}... (length: {len(self.token)})")
            logger.debug(f"📡 Token contains special chars: {not self.token.replace('-', '').replace('_', '').isalnum()}")
            
            # WebSocket 연결 (추가 헤더 없이, 타임아웃 설정)
            # ElevenLabs는 토큰을 쿼리 파라미터로만 받습니다
            logger.info(f"🔗 Attempting WebSocket connection to ElevenLabs...")
            
            # WebSocket 연결 시도
            self.websocket = await websockets.connect(
                url,
                ping_interval=None,  # ping 비활성화
                ping_timeout=None,
                close_timeout=10,
            )
            
            logger.info(f"✅ WebSocket connection established!")
            
            self.is_connected = True
            self.reconnect_attempts = 0
            
            # 세션 시작 메시지 대기 (서버에서 session_started 메시지를 보냄)
            # 메시지 수신 태스크 시작
            self.connection_task = asyncio.create_task(self._receive_messages())
            
            logger.info(f"✅ ElevenLabs STT connected (model: {self.model_id}, sample_rate: {self.sample_rate}, language: {self.language or 'auto'})")
            
        except websockets.exceptions.InvalidStatusCode as e:
            logger.error(f"❌ ElevenLabs STT connection error: HTTP {e.status_code}")
            
            # HTTP 응답 본문 읽기 시도 (있을 경우)
            try:
                if hasattr(e, 'response') and e.response:
                    response_body = await e.response.text()
                    logger.error(f"❌ Response body: {response_body}")
            except:
                pass
            
            if e.status_code == 403:
                logger.error(f"💡 HTTP 403: Authentication failed")
                logger.error(f"💡 Possible causes:")
                logger.error(f"💡   1. Token is invalid or expired (token length: {len(self.token) if self.token else 0})")
                logger.error(f"💡   2. API key does not have access to Scribe Realtime v2")
                logger.error(f"💡   3. Scribe Realtime v2 requires a paid plan")
                logger.error(f"💡   4. WebSocket URL format may be incorrect")
                logger.error(f"💡   5. Token generation may have failed silently")
                logger.error(f"💡 Solutions:")
                logger.error(f"💡   - Check if ELEVENLABS_API_KEY is correct in .env file")
                logger.error(f"💡   - Verify your ElevenLabs account has access to Scribe Realtime v2")
                logger.error(f"💡   - Check if your plan includes Scribe Realtime v2")
                logger.error(f"💡   - Try generating a new token")
                logger.error(f"💡 Token format check: {self.token[:20] if self.token else 'None'}...")
            elif e.status_code == 401:
                logger.error(f"💡 HTTP 401: Unauthorized")
                logger.error(f"💡 Token is invalid or expired")
                logger.error(f"💡 Check if token was generated correctly")
            elif e.status_code == 404:
                logger.error(f"💡 HTTP 404: WebSocket endpoint not found")
                logger.error(f"💡 Check if WebSocket URL is correct")
                logger.error(f"💡 URL: {base_url}")
            else:
                logger.error(f"💡 HTTP {e.status_code}: Unexpected error")
                logger.error(f"💡 Check ElevenLabs API status and documentation")
            
            self.is_connected = False
            raise
        except Exception as e:
            logger.error(f"❌ ElevenLabs STT connection error: {e}")
            logger.error(f"💡 Error type: {type(e).__name__}")
            logger.error(f"💡 Error details: {str(e)}")
            logger.error(f"💡 Token length: {len(self.token) if self.token else 0}")
            logger.error(f"💡 Check if ELEVENLABS_API_KEY is correct in .env file")
            self.is_connected = False
            raise
    
    async def _send_session_config(self):
        """세션 설정 전송 (실제 API에서는 필요 없을 수 있음)"""
        # ElevenLabs Scribe Realtime v2는 WebSocket 연결 시 자동으로 세션을 시작합니다
        # 필요시 여기서 추가 설정을 전송할 수 있습니다
        pass
    
    async def _receive_messages(self):
        """WebSocket 메시지 수신 루프"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"❌ Error handling message: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.warning("⚠️ ElevenLabs WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"❌ Error receiving messages: {e}")
            self.is_connected = False
    
    async def _handle_message(self, data: dict):
        """ElevenLabs 메시지 처리"""
        message_type = data.get("type")
        
        if message_type == "session_started":
            logger.info("✅ ElevenLabs session started")
            # 세션 설정 확인
            session_config = data.get("session", {})
            logger.debug(f"Session config: {session_config}")
        
        elif message_type == "partial_transcript":
            # 부분 전사 결과 (실시간 업데이트)
            text = data.get("text", "")
            if text:
                self.partial_transcript = text
                # 부분 전사는 로깅만 (아직 TranscriptionFrame 생성 안 함)
                logger.debug(f"📝 Partial: {text}")
        
        elif message_type == "committed_transcript":
            # 확정된 전사 결과 (최종)
            text = data.get("text", "")
            if text and text.strip():
                self.last_committed_transcript = text.strip()
                self.partial_transcript = ""
                
                # TranscriptionFrame 생성 및 전달
                logger.info(f"✅ Committed: {text.strip()}")
                frame = TranscriptionFrame(text=text.strip(), user_id="user")
                await self.push_frame(frame, FrameDirection.DOWNSTREAM)
        
        elif message_type == "committed_transcript_with_timestamps":
            # 타임스탬프 포함 전사 결과
            text = data.get("text", "")
            if text and text.strip():
                self.last_committed_transcript = text.strip()
                self.partial_transcript = ""
                
                # TranscriptionFrame 생성 및 전달
                logger.info(f"✅ Committed (with timestamps): {text.strip()}")
                frame = TranscriptionFrame(text=text.strip(), user_id="user")
                await self.push_frame(frame, FrameDirection.DOWNSTREAM)
        
        elif message_type == "error":
            error = data.get("error", {})
            error_type = error.get("type", "unknown")
            error_message = error.get("message", "Unknown error")
            logger.error(f"❌ ElevenLabs error ({error_type}): {error_message}")
            self.is_connected = False
        
        elif message_type == "auth_error":
            error = data.get("error", {})
            error_message = error.get("message", "Authentication error")
            logger.error(f"❌ ElevenLabs authentication error: {error_message}")
            self.is_connected = False
        
        elif message_type == "quota_exceeded":
            error = data.get("error", {})
            error_message = error.get("message", "Quota exceeded")
            logger.error(f"❌ ElevenLabs quota exceeded: {error_message}")
            self.is_connected = False
        
        elif message_type == "transcriber_error":
            error = data.get("error", {})
            error_message = error.get("message", "Transcriber error")
            logger.error(f"❌ ElevenLabs transcriber error: {error_message}")
        
        elif message_type == "input_error":
            error = data.get("error", {})
            error_message = error.get("message", "Input error")
            logger.error(f"❌ ElevenLabs input error: {error_message}")
    
    async def _send_audio(self, audio_data: bytes):
        """오디오 데이터를 ElevenLabs로 전송"""
        if not self.is_connected or not self.websocket:
            return
        
        try:
            # PCM 오디오를 base64로 인코딩
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # 오디오 청크 전송 (실제 API 형식에 맞게)
            message = {
                "type": "input_audio_chunk",
                "audio_base_64": audio_base64,
                "sample_rate": self.sample_rate,
            }
            
            await self.websocket.send(json.dumps(message))
            
        except websockets.exceptions.ConnectionClosed:
            logger.warning("⚠️ ElevenLabs WebSocket connection closed while sending audio")
            self.is_connected = False
        except Exception as e:
            logger.error(f"❌ Error sending audio: {e}")
            self.is_connected = False
    
    async def _commit_transcript(self):
        """전사 세그먼트 확정 (수동 커밋)"""
        if not self.is_connected or not self.websocket:
            return
        
        try:
            # ElevenLabs API에 따르면 commit 메시지를 보내면 확정된 transcript를 받습니다
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
                try:
                    await self._connect()
                    # 연결 후 잠시 대기 (세션 시작 대기)
                    await asyncio.sleep(0.1)
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
                    await self._send_audio(audio_bytes)
        
        # 다른 프레임은 그대로 전달
        else:
            await self.push_frame(frame, direction)
    
    async def cleanup(self):
        """정리 작업"""
        self.is_connected = False
        
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
        
        logger.info("🧹 ElevenLabs STT cleanup completed")

