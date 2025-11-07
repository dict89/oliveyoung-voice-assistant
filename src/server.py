"""
FastAPI 서버 - Daily.co 룸 생성 및 봇 관리
"""
import os
import asyncio
from typing import Optional
from datetime import datetime, timedelta

import aiohttp
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
import json
from loguru import logger
from dotenv import load_dotenv

from .bot import OliveYoungVoiceBot
from . import websocket_manager

# 환경 변수 로드
load_dotenv()

app = FastAPI(title="올리브영 음성 쇼핑 어시스턴트 API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Daily API 설정
DAILY_API_KEY = os.getenv("DAILY_API_KEY")
DAILY_API_URL = "https://api.daily.co/v1"


class RoomRequest(BaseModel):
    """룸 생성 요청"""
    duration_minutes: Optional[int] = 30
    

class RoomResponse(BaseModel):
    """룸 생성 응답"""
    room_url: str
    room_name: str
    token: Optional[str] = None
    expires: str


async def create_daily_room(duration_minutes: int = 30) -> dict:
    """
    Daily.co 룸을 생성합니다.
    
    Args:
        duration_minutes: 룸 유효 시간 (분)
        
    Returns:
        룸 정보 딕셔너리
    """
    if not DAILY_API_KEY:
        raise ValueError("DAILY_API_KEY가 설정되지 않았습니다.")
    
    # 만료 시간 계산 (UTC)
    from datetime import timezone
    expires = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
    
    headers = {
        "Authorization": f"Bearer {DAILY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 룸 설정
    room_config = {
        "properties": {
            "exp": int(expires.timestamp()),
            "enable_chat": True,
            "enable_transcription": False,  # Cartesia STT 사용
            "enable_recording": False,
            "max_participants": 2,  # 사용자 1명 + 봇 1명
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{DAILY_API_URL}/rooms",
            headers=headers,
            json=room_config
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Failed to create room: {error_text}")
                raise HTTPException(status_code=500, detail="룸 생성에 실패했습니다.")
            
            room_data = await response.json()
            
            # 봇용 token 생성 (transcription 권한 필요)
            token_config = {
                "properties": {
                    "room_name": room_data["name"],
                    "is_owner": True,
                    "exp": int(expires.timestamp())
                }
            }
            
            async with session.post(
                f"{DAILY_API_URL}/meeting-tokens",
                headers=headers,
                json=token_config
            ) as token_response:
                if token_response.status == 200:
                    token_data = await token_response.json()
                    bot_token = token_data["token"]
                else:
                    logger.warning("Failed to create token, proceeding without it")
                    bot_token = None
            
            return {
                "room_url": room_data["url"],
                "room_name": room_data["name"],
                "token": bot_token,
                "expires": expires.isoformat()
            }


@app.get("/", response_class=HTMLResponse)
async def root():
    """루트 페이지 - 웹 인터페이스"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>올리브영 음성 쇼핑 어시스턴트</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            
            .container {
                background: white;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                max-width: 800px;
                width: 100%;
            }
            
            h1 {
                color: #333;
                text-align: center;
                margin-bottom: 10px;
                font-size: 2em;
            }
            
            .subtitle {
                text-align: center;
                color: #666;
                margin-bottom: 30px;
                font-size: 1.1em;
            }
            
            .status {
                padding: 15px;
                margin: 20px 0;
                border-radius: 10px;
                text-align: center;
                font-weight: 500;
                display: none;
            }
            
            .status.info {
                background: #d1ecf1;
                color: #0c5460;
                border: 1px solid #bee5eb;
            }
            
            .status.success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            
            .status.error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            
            .btn {
                display: block;
                width: 100%;
                padding: 18px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 18px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                margin: 10px 0;
            }
            
            .btn:hover:not(:disabled) {
                background: #5568d3;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }
            
            .btn:disabled {
                background: #ccc;
                cursor: not-allowed;
                transform: none;
            }
            
            #videoContainer {
                margin: 20px 0;
                display: none;
            }
            
            .feature-list {
                list-style: none;
                padding: 0;
                margin: 30px 0 20px 0;
            }
            
            .feature-list li {
                padding: 12px 15px;
                margin: 8px 0;
                background: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #667eea;
                transition: all 0.3s;
            }
            
            .feature-list li:hover {
                transform: translateX(5px);
                background: #e9ecef;
            }
            
            .feature-list li:before {
                content: "✓ ";
                color: #667eea;
                font-weight: bold;
                margin-right: 10px;
            }
            
            .example-questions {
                background: #f0f4ff;
                padding: 20px;
                border-radius: 10px;
                margin-top: 20px;
            }
            
            .example-questions h3 {
                color: #667eea;
                margin-bottom: 15px;
            }
            
            .example-questions ul {
                list-style: none;
                padding: 0;
            }
            
            .example-questions li {
                padding: 10px;
                margin: 5px 0;
                background: white;
                border-radius: 5px;
                color: #495057;
            }
            
            .example-questions li:before {
                content: "💬 ";
                margin-right: 8px;
            }
            
            /* Face Detection Status */
            .face-status {
                position: fixed;
                top: 20px;
                right: 20px;
                display: none;
                align-items: center;
                background: white;
                padding: 12px 20px;
                border-radius: 30px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                z-index: 1000;
                font-size: 14px;
                font-weight: 500;
            }
            
            .face-status.active {
                display: flex;
            }
            
            .face-status-icon {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 10px;
                animation: pulse 2s infinite;
            }
            
            .face-status-icon.green {
                background: #28a745;
                box-shadow: 0 0 10px rgba(40, 167, 69, 0.5);
            }
            
            .face-status-icon.red {
                background: #dc3545;
                box-shadow: 0 0 10px rgba(220, 53, 69, 0.5);
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.6; }
            }
            
            .face-status-text {
                color: #495057;
            }
        </style>
    </head>
    <body>
        <!-- Face Detection Status Indicator -->
        <div id="faceStatus" class="face-status">
            <div id="faceStatusIcon" class="face-status-icon red"></div>
            <span id="faceStatusText" class="face-status-text">카메라 대기중...</span>
        </div>
        
        <div class="container">
            <h1>🛍️ 올리브영 음성 쇼핑 어시스턴트</h1>
            <p class="subtitle">AI 음성 봇과 대화하며 매장 정보를 확인하세요</p>
            
            <div id="status" class="status"></div>
            
            <!-- 언어 선택 -->
            <div style="margin: 20px 0; text-align: center;">
                <label style="font-size: 16px; margin-right: 10px;">🌐 언어 선택:</label>
                <label style="margin-right: 20px;">
                    <input type="radio" name="language" value="ko" checked> 한국어
                </label>
                <label>
                    <input type="radio" name="language" value="en"> English
                </label>
            </div>
            
            <button id="startBtn" class="btn" onclick="startConversation()">
                🎙️ 대화 시작하기
            </button>
            
            <div id="videoContainer"></div>
            
            <div id="chatContainer" class="chat-container">
                <h3 style="margin: 0 0 15px 0; color: #667eea;">💬 대화 내역</h3>
                <div id="chatHistory"></div>
            </div>
            
            <h3 style="margin-top: 30px; color: #333;">주요 기능</h3>
            <ul class="feature-list">
                <li>실시간 음성 대화</li>
                <li>올리브영 매장 위치 및 정보 안내</li>
                <li>영업시간 및 연락처 제공</li>
                <li>인기 제품 추천</li>
                <li>교통 정보 및 주변 랜드마크 안내</li>
            </ul>
            
            <div class="example-questions">
                <h3>질문 예시</h3>
                <ul>
                    <li>"강남역 근처 올리브영 어디 있어요?"</li>
                    <li>"명동점 영업시간 알려주세요"</li>
                    <li>"인기 있는 제품 추천해주세요"</li>
                    <li>"홍대 매장에서 피부 진단 서비스 있나요?"</li>
                </ul>
            </div>
        </div>
        
        <script src="https://unpkg.com/@daily-co/daily-js"></script>
        <script defer src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs"></script>
        <script defer src="https://cdn.jsdelivr.net/npm/@tensorflow-models/blazeface"></script>
        <script>
            let callFrame = null;
            let faceDetectionActive = false;
            let isFacingForward = false;
            let faceDetectionInterval = null;
            let inactivityTimer = null;
            const INACTIVITY_TIMEOUT = 5 * 60 * 1000; // 5분 (밀리초)
            
            function showStatus(message, type) {
                const status = document.getElementById('status');
                status.textContent = message;
                status.className = 'status ' + type;
                status.style.display = 'block';
            }
            
            function addChatMessage(speaker, message) {
                const chatHistory = document.getElementById('chatHistory');
                
                const messageDiv = document.createElement('div');
                messageDiv.className = `chat-message ${speaker}`;
                
                const now = new Date();
                const timeString = now.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
                
                messageDiv.innerHTML = `
                    <div class="speaker">${speaker === 'user' ? '👤 나' : '🤖 어시스턴트'}</div>
                    <div>${message}</div>
                    <div class="timestamp">${timeString}</div>
                `;
                
                chatHistory.appendChild(messageDiv);
                
                // 스크롤을 맨 아래로
                chatHistory.scrollTop = chatHistory.scrollHeight;
            }
            
            function clearChat() {
                const chatHistory = document.getElementById('chatHistory');
                chatHistory.innerHTML = '';
            }
            
            // Inactivity Timeout Functions
            function resetInactivityTimer() {
                // 기존 타이머 취소
                if (inactivityTimer) {
                    clearTimeout(inactivityTimer);
                }
                
                // 새로운 타이머 시작 (5분)
                inactivityTimer = setTimeout(() => {
                    console.warn('⏰ Inactivity timeout (5 minutes). Ending session...');
                    showStatus('⏰ 5분간 대화가 없어 세션이 종료됩니다.', 'warning');
                    
                    // 세션 종료
                    setTimeout(() => {
                        if (callFrame) {
                            callFrame.leave();
                        }
                        stopFaceDetection();
                    }, 2000);
                }, INACTIVITY_TIMEOUT);
                
                console.log('⏱️ Inactivity timer reset (5 min)');
            }
            
            function stopInactivityTimer() {
                if (inactivityTimer) {
                    clearTimeout(inactivityTimer);
                    inactivityTimer = null;
                    console.log('⏱️ Inactivity timer stopped');
                }
            }
            
            // Face Detection Functions
            let blazefaceModel = null;
            let localVideoStream = null;
            let localVideoElement = null;
            
            async function loadFaceDetectionModel() {
                try {
                    console.log('Loading BlazeFace model...');
                    blazefaceModel = await blazeface.load();
                    console.log('BlazeFace model loaded');
                } catch (error) {
                    console.error('Failed to load BlazeFace model:', error);
                }
            }
            
            async function initializeLocalVideo() {
                try {
                    // 로컬 비디오 스트림 가져오기 (한 번만)
                    localVideoStream = await navigator.mediaDevices.getUserMedia({ 
                        video: { width: 640, height: 480 }, 
                        audio: false 
                    });
                    
                    // video element 생성 (디버깅용으로 보이게 설정)
                    localVideoElement = document.createElement('video');
                    localVideoElement.srcObject = localVideoStream;
                    localVideoElement.autoplay = true;
                    localVideoElement.muted = true;
                    localVideoElement.playsInline = true;  // iOS 호환성
                    localVideoElement.width = 640;
                    localVideoElement.height = 480;
                    
                    // 디버깅용: 작은 미리보기로 표시
                    localVideoElement.style.position = 'fixed';
                    localVideoElement.style.bottom = '20px';
                    localVideoElement.style.right = '20px';
                    localVideoElement.style.width = '160px';
                    localVideoElement.style.height = '120px';
                    localVideoElement.style.border = '2px solid #667eea';
                    localVideoElement.style.borderRadius = '10px';
                    localVideoElement.style.zIndex = '999';
                    document.body.appendChild(localVideoElement);
                    
                    // video가 재생될 때까지 대기
                    await new Promise((resolve, reject) => {
                        const timeout = setTimeout(() => reject(new Error('Video load timeout')), 5000);
                        
                        localVideoElement.onloadeddata = () => {
                            clearTimeout(timeout);
                            console.log(`✅ Local video stream ready: ${localVideoElement.videoWidth}x${localVideoElement.videoHeight}`);
                            resolve();
                        };
                        
                        localVideoElement.onerror = (e) => {
                            clearTimeout(timeout);
                            reject(e);
                        };
                    });
                    
                    // 재생 시작
                    await localVideoElement.play();
                    console.log('✅ Video playing');
                    
                    return true;
                } catch (error) {
                    console.error('Failed to initialize local video:', error);
                    return false;
                }
            }
            
            function updateFaceStatus(isFacing) {
                const statusDiv = document.getElementById('faceStatus');
                const statusIcon = document.getElementById('faceStatusIcon');
                const statusText = document.getElementById('faceStatusText');
                
                statusDiv.classList.add('active');
                
                if (isFacing) {
                    statusIcon.className = 'face-status-icon green';
                    statusText.textContent = '🎤 마이크 활성 (정면 인식)';
                } else {
                    statusIcon.className = 'face-status-icon red';
                    statusText.textContent = '⏸️ 마이크 대기 (정면을 봐주세요)';
                }
            }
            
            async function detectFace(videoElement) {
                if (!blazefaceModel) {
                    console.warn('BlazeFace model not ready');
                    return false;
                }
                
                if (!videoElement) {
                    console.warn('Video element not ready');
                    return false;
                }
                
                // 비디오 상태 확인
                if (videoElement.readyState < 2) {
                    console.warn(`Video not ready: readyState=${videoElement.readyState}`);
                    return false;
                }
                
                if (videoElement.videoWidth === 0 || videoElement.videoHeight === 0) {
                    console.warn(`Video has no dimensions: ${videoElement.videoWidth}x${videoElement.videoHeight}`);
                    return false;
                }
                
                try {
                    // BlazeFace 예측
                    const predictions = await blazefaceModel.estimateFaces(videoElement, false);
                    
                    console.log(`🔍 BlazeFace predictions: ${predictions.length} face(s) detected`);
                    
                    if (predictions.length > 0) {
                        const face = predictions[0];
                        
                        // 얼굴 크기로 거리 판단 (정면: 얼굴이 충분히 크게 보임)
                        const landmarks = face.landmarks;
                        const leftEye = landmarks[0];
                        const rightEye = landmarks[1];
                        const eyeDistance = Math.sqrt(
                            Math.pow(rightEye[0] - leftEye[0], 2) + 
                            Math.pow(rightEye[1] - leftEye[1], 2)
                        );
                        
                        // 얼굴 박스 크기
                        const faceWidth = face.bottomRight[0] - face.topLeft[0];
                        const faceHeight = face.bottomRight[1] - face.topLeft[1];
                        
                        // 정면 판단: 얼굴 크기가 일정 이상 (임계값 완화)
                        const isFrontal = faceWidth > 50 && faceHeight > 50 && eyeDistance > 20;
                        
                        console.log(`✅ Face detected: width=${faceWidth.toFixed(0)}, height=${faceHeight.toFixed(0)}, eyeDist=${eyeDistance.toFixed(0)}, frontal=${isFrontal}`);
                        
                        return isFrontal;
                    } else {
                        console.log(`❌ No face detected (video: ${videoElement.videoWidth}x${videoElement.videoHeight}, playing: ${!videoElement.paused})`);
                        return false;
                    }
                } catch (error) {
                    console.error('Face detection error:', error);
                    return false;
                }
            }
            
            async function startFaceDetection() {
                if (faceDetectionInterval) return;
                
                console.log('Starting face detection (1 fps)...');
                
                // 로컬 비디오 초기화 (한 번만)
                const videoReady = await initializeLocalVideo();
                if (!videoReady || !localVideoElement) {
                    console.error('Failed to initialize video for face detection');
                    updateFaceStatus(false);
                    return;
                }
                
                // 1초에 1번 체크
                faceDetectionInterval = setInterval(async () => {
                    if (!callFrame || !localVideoElement) {
                        console.warn('callFrame or localVideoElement not ready');
                        return;
                    }
                    
                    try {
                        const participants = callFrame.participants();
                        const localParticipant = participants.local;
                        
                        if (!localParticipant) {
                            console.warn('Local participant not found');
                            return;
                        }
                        
                        console.log(`👤 Local participant video: ${localParticipant.video ? 'ON' : 'OFF'}`);
                        
                        if (!localParticipant.video) {
                            isFacingForward = false;
                            updateFaceStatus(false);
                            // Daily.co 마이크 mute
                            await callFrame.setLocalAudio(false);
                            return;
                        }
                        
                        // 얼굴 감지 (재사용 video element)
                        const wasFacing = isFacingForward;
                        isFacingForward = await detectFace(localVideoElement);
                        
                        console.log(`📊 Face detection result: wasFacing=${wasFacing}, isFacingForward=${isFacingForward}`);
                        
                        // 상태 업데이트
                        updateFaceStatus(isFacingForward);
                        
                        // Daily.co 마이크 제어 (mute/unmute)
                        if (isFacingForward !== wasFacing && callFrame) {
                            console.log(`🔄 Changing microphone state: ${wasFacing} → ${isFacingForward}`);
                            await callFrame.setLocalAudio(isFacingForward);
                            console.log(`🎤 Microphone ${isFacingForward ? 'UNMUTED ✅' : 'MUTED ⏸️'}`);
                            
                            // 상태 확인
                            const currentState = await callFrame.localAudio();
                            console.log(`✓ Current microphone state confirmed: ${currentState}`);
                        }
                        
                    } catch (error) {
                        console.error('Face detection loop error:', error);
                    }
                }, 1000); // 1초마다
                
                faceDetectionActive = true;
            }
            
            function stopFaceDetection() {
                if (faceDetectionInterval) {
                    clearInterval(faceDetectionInterval);
                    faceDetectionInterval = null;
                }
                faceDetectionActive = false;
                
                // 비디오 스트림 정리
                if (localVideoStream) {
                    localVideoStream.getTracks().forEach(track => track.stop());
                    localVideoStream = null;
                }
                if (localVideoElement) {
                    localVideoElement.srcObject = null;
                    if (localVideoElement.parentNode) {
                        localVideoElement.parentNode.removeChild(localVideoElement);
                    }
                    localVideoElement = null;
                }
                
                const statusDiv = document.getElementById('faceStatus');
                statusDiv.classList.remove('active');
                
                console.log('Face detection stopped and resources cleaned up');
            }
            
            async function startConversation() {
                const btn = document.getElementById('startBtn');
                btn.disabled = true;
                showStatus('룸을 생성하는 중...', 'info');
                
                // 얼굴 인식 모델 로드
                if (!blazefaceModel) {
                    showStatus('얼굴 인식 모델 로딩 중...', 'info');
                    await loadFaceDetectionModel();
                }
                
                try {
                    // 룸 생성 요청
                    const response = await fetch('/api/create-room', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            duration_minutes: 30
                        })
                    });
                    
                    if (!response.ok) {
                        throw new Error('룸 생성 실패');
                    }
                    
                    const data = await response.json();
                    showStatus('연결 중... 잠시만 기다려주세요.', 'info');
                    
                    // Daily.co 클라이언트 생성
                    console.log('Creating Daily iframe...');
                    callFrame = DailyIframe.createFrame(
                        document.getElementById('videoContainer'),
                        {
                            showLeaveButton: true,
                            showFullscreenButton: false,
                            iframeStyle: {
                                width: '100%',
                                height: '500px',
                                border: 'none',
                                borderRadius: '10px'
                            }
                        }
                    );
                    
                    document.getElementById('videoContainer').style.display = 'block';
                    
                    // 룸 참여 (사용자 먼저) - 타임아웃 추가
                    console.log('Joining room:', data.room_url);
                    
                    const joinPromise = callFrame.join({ url: data.room_url });
                    const timeoutPromise = new Promise((_, reject) => 
                        setTimeout(() => reject(new Error('Daily.co 연결 타임아웃 (30초)')), 30000)
                    );
                    
                    const joinResult = await Promise.race([joinPromise, timeoutPromise]);
                    console.log('Join result:', joinResult);
                    
                    // 초기 마이크 꺼진 상태 (얼굴 인식으로 제어)
                    callFrame.setLocalAudio(false);
                    console.log('Initial microphone state: DISABLED (face detection pending)');
                    
                    showStatus('봇이 참여하는 중... 잠시만 기다려주세요.', 'info');
                    
                    // 선택된 언어 가져오기
                    const selectedLanguage = document.querySelector('input[name="language"]:checked').value;
                    console.log('Selected language:', selectedLanguage);
                    
                    // 사용자가 참여한 후 봇 시작 (token + language 전달)
                    await fetch('/api/start-bot', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            room_url: data.room_url,
                            room_name: data.room_name,
                            token: data.token,
                            language: selectedLanguage
                        })
                    });
                    
                    // 잠시 대기 후 성공 메시지 및 얼굴 인식 시작
                    setTimeout(async () => {
                        showStatus('✅ 연결되었습니다! 정면을 바라보면 마이크가 활성화됩니다.', 'success');
                        
                        // 얼굴 인식 시작 (1초에 1번 체크)
                        await startFaceDetection();
                        
                        // 비활성 타이머 시작 (5분)
                        resetInactivityTimer();
                    }, 2000);
                    
                    // 채팅창 초기화
                    clearChat();
                    addChatMessage('assistant', '안녕하세요! 올리브영 쇼핑 어시스턴트입니다. 정면을 바라보시면 질문하실 수 있습니다.');
                    
                    // WebSocket 연결 (OpenAI Whisper 결과 수신용)
                    const chatProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const chatWs = new WebSocket(`${chatProtocol}//${window.location.host}/api/chat-ws`);
                    
                    chatWs.onopen = () => {
                        console.log('✅ Chat WebSocket connected');
                        
                        // 연결 유지를 위한 ping (5초마다)
                        setInterval(() => {
                            if (chatWs.readyState === WebSocket.OPEN) {
                                chatWs.send('ping');
                            }
                        }, 5000);
                    };
                    
                    chatWs.onmessage = (event) => {
                        try {
                            const data = JSON.parse(event.data);
                            console.log('📝 Received from server:', data);
                            
                            if (data.type === 'transcript' && data.speaker === 'user' && data.text) {
                                console.log('✅ Adding user message:', data.text);
                                addChatMessage('user', data.text);
                                
                                // Intent:YES로 통과한 메시지 → 비활성 타이머 리셋
                                resetInactivityTimer();
                            } else if (data.type === 'response' && data.speaker === 'assistant' && data.text) {
                                console.log('✅ Adding assistant message:', data.text);
                                addChatMessage('assistant', data.text);
                            }
                        } catch (e) {
                            console.error('Error parsing chat message:', e);
                        }
                    };
                    
                    chatWs.onerror = (error) => {
                        console.error('Chat WebSocket error:', error);
                    };
                    
                    chatWs.onclose = () => {
                        console.log('Chat WebSocket closed');
                    };
                    
                    // 통화 종료 이벤트 처리
                    callFrame.on('left-meeting', () => {
                        document.getElementById('videoContainer').style.display = 'none';
                        btn.disabled = false;
                        showStatus('대화가 종료되었습니다.', 'info');
                        
                        // 얼굴 인식 중지
                        stopFaceDetection();
                        
                        // 비활성 타이머 중지
                        stopInactivityTimer();
                    });
                    
                } catch (error) {
                    console.error('Error:', error);
                    
                    // 얼굴 인식 중지
                    stopFaceDetection();
                    
                    // 비활성 타이머 중지
                    stopInactivityTimer();
                    
                    // 에러 타입별 처리
                    let errorMessage = '오류가 발생했습니다: ' + error.message;
                    
                    if (error.message.includes('타임아웃')) {
                        errorMessage = 'Daily.co 연결 시간 초과. 인터넷 연결을 확인하거나 다시 시도해주세요.';
                    } else if (error.message.includes('룸 생성')) {
                        errorMessage = 'Daily.co API 키를 확인해주세요. .env 파일에 DAILY_API_KEY가 설정되어 있나요?';
                    }
                    
                    showStatus(errorMessage, 'error');
                    btn.disabled = false;
                    
                    // Daily iframe 정리
                    if (callFrame) {
                        try {
                            await callFrame.destroy();
                        } catch (e) {
                            console.log('Error destroying frame:', e);
                        }
                        callFrame = null;
                    }
                    document.getElementById('videoContainer').style.display = 'none';
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/api/create-room", response_model=RoomResponse)
async def create_room(request: RoomRequest):
    """
    Daily.co 룸을 생성합니다.
    """
    try:
        room_data = await create_daily_room(request.duration_minutes)
        return RoomResponse(**room_data)
    except Exception as e:
        logger.error(f"Error creating room: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BotStartRequest(BaseModel):
    """봇 시작 요청"""
    room_url: str
    room_name: str
    token: Optional[str] = None
    language: Optional[str] = "ko"  # 기본값: 한국어 (ko/en)


@app.post("/api/start-bot")
async def start_bot(request: BotStartRequest):
    """
    봇을 시작합니다.
    """
    try:
        # 백그라운드에서 봇 실행 (언어 설정 전달)
        bot = OliveYoungVoiceBot()
        asyncio.create_task(bot.run(request.room_url, request.token, request.language))
        
        return JSONResponse(
            content={
                "status": "started",
                "room_name": request.room_name,
                "message": "봇이 시작되었습니다."
            }
        )
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/api/chat-ws")
async def chat_websocket(websocket: WebSocket):
    """채팅 메시지 전송용 WebSocket"""
    from fastapi import WebSocketDisconnect
    
    await websocket.accept()
    client_id = id(websocket)
    websocket_manager.add_websocket(client_id, websocket)
    
    try:
        # 연결 유지 (메시지 수신 대기)
        while True:
            data = await websocket.receive_text()
            # ping 메시지는 무시
            if data != 'ping':
                logger.debug(f"Received from client {client_id}: {data}")
    except WebSocketDisconnect:
        logger.info(f"❌ Chat WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"❌ Chat WebSocket error {client_id}: {e}")
    finally:
        websocket_manager.remove_websocket(client_id)


@app.get("/api/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "service": "oliveyoung-voice-assistant"}


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
