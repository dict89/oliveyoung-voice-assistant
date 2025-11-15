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
from pipecat.frames.frames import AudioFrame, TranscriptionFrame, Frame
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
            # WebSocket URL (token을 쿼리 파라미터로 전달)
            url = f"wss://api.elevenlabs.io/v1/speech-to-text/realtime/websocket?token={self.token}"
            
            # 추가 쿼리 파라미터
            query_params = []
            if self.language:
                query_params.append(f"language={self.language}")
            
            if query_params:
                url += "&" + "&".join(query_params)
            
            # WebSocket 연결
            self.websocket = await websockets.connect(url)
            
            self.is_connected = True
            self.reconnect_attempts = 0
            
            # 세션 시작 메시지 대기 (서버에서 session_started 메시지를 보냄)
            # 메시지 수신 태스크 시작
            self.connection_task = asyncio.create_task(self._receive_messages())
            
            logger.info(f"✅ ElevenLabs STT connected (model: {self.model_id}, sample_rate: {self.sample_rate})")
            
        except Exception as e:
            logger.error(f"❌ ElevenLabs STT connection error: {e}")
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
        """프레임 처리 (AudioFrame을 받아서 TranscriptionFrame 생성)"""
        await super().process_frame(frame, direction)
        
        # AudioFrame 처리
        if isinstance(frame, AudioFrame):
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
            audio_data = frame.audio
            
            # Daily.co는 16kHz PCM으로 오디오를 제공하는 것으로 가정
            # 실제로는 frame.audio 형식에 따라 변환이 필요할 수 있음
            if audio_data is not None:
                # audio_data 형식 변환 (bytes로 변환)
                audio_bytes = None
                
                if isinstance(audio_data, bytes):
                    audio_bytes = audio_data
                elif isinstance(audio_data, bytearray):
                    audio_bytes = bytes(audio_data)
                else:
                    # numpy array 등의 경우 bytes로 변환
                    try:
                        import numpy as np
                        if isinstance(audio_data, np.ndarray):
                            # numpy array를 int16으로 변환 후 bytes로 변환
                            # Daily.co는 보통 float32 (-1.0 ~ 1.0) 또는 int16 형식
                            if audio_data.dtype == np.float32:
                                # float32를 int16으로 변환
                                audio_int16 = (audio_data * 32767).astype(np.int16)
                                audio_bytes = audio_int16.tobytes()
                            elif audio_data.dtype == np.int16:
                                audio_bytes = audio_data.tobytes()
                            else:
                                logger.warning(f"⚠️ Unsupported numpy dtype: {audio_data.dtype}")
                                return
                        else:
                            logger.warning(f"⚠️ Unsupported audio format: {type(audio_data)}")
                            return
                    except ImportError:
                        logger.warning("⚠️ numpy not available, cannot convert audio data")
                        return
                    except Exception as e:
                        logger.error(f"❌ Error converting audio data: {e}")
                        return
                
                # 오디오 데이터 전송
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

