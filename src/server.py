"""
FastAPI 서버 - WebSocket 기반 음성 챗봇
"""
import os
import asyncio
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from loguru import logger
from dotenv import load_dotenv

from pipecat.transports.websocket.fastapi import FastAPIWebsocketTransport

from .bot import OliveYoungVoiceBot

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
            
            .status.recording {
                background: #fff3cd;
                color: #856404;
                border: 1px solid #ffeaa7;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
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
            
            .btn.stop {
                background: #e74c3c;
            }
            
            .btn.stop:hover:not(:disabled) {
                background: #c0392b;
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
            
            .audio-visualizer {
                height: 60px;
                background: #f8f9fa;
                border-radius: 10px;
                margin: 20px 0;
                display: none;
                justify-content: center;
                align-items: center;
                gap: 4px;
                padding: 10px;
            }
            
            .audio-visualizer.active {
                display: flex;
            }
            
            .bar {
                width: 4px;
                height: 20px;
                background: #667eea;
                border-radius: 2px;
                animation: wave 1s ease-in-out infinite;
            }
            
            .bar:nth-child(2) { animation-delay: 0.1s; }
            .bar:nth-child(3) { animation-delay: 0.2s; }
            .bar:nth-child(4) { animation-delay: 0.3s; }
            .bar:nth-child(5) { animation-delay: 0.4s; }
            
            @keyframes wave {
                0%, 100% { height: 20px; }
                50% { height: 40px; }
            }
            
            .chat-container {
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
                max-height: 400px;
                overflow-y: auto;
                display: none;
            }
            
            .chat-container.active {
                display: block;
            }
            
            .chat-message {
                margin: 10px 0;
                padding: 12px 16px;
                border-radius: 10px;
                max-width: 80%;
                word-wrap: break-word;
                animation: fadeIn 0.3s ease-in;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .chat-message.user {
                background: #667eea;
                color: white;
                margin-left: auto;
                text-align: right;
            }
            
            .chat-message.assistant {
                background: white;
                color: #333;
                border: 1px solid #dee2e6;
            }
            
            .chat-message .timestamp {
                font-size: 0.75em;
                opacity: 0.7;
                margin-top: 4px;
            }
            
            .chat-message .speaker {
                font-weight: bold;
                margin-bottom: 4px;
            }
            
            .chat-container::-webkit-scrollbar {
                width: 8px;
            }
            
            .chat-container::-webkit-scrollbar-track {
                background: #f1f1f1;
                border-radius: 10px;
            }
            
            .chat-container::-webkit-scrollbar-thumb {
                background: #667eea;
                border-radius: 10px;
            }
            
            .chat-container::-webkit-scrollbar-thumb:hover {
                background: #5568d3;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛍️ 올리브영 음성 쇼핑 어시스턴트</h1>
            <p class="subtitle">AI 음성 봇과 대화하며 매장 정보를 확인하세요</p>
            
            <div id="status" class="status"></div>
            
            <div id="audioVisualizer" class="audio-visualizer">
                <div class="bar"></div>
                <div class="bar"></div>
                <div class="bar"></div>
                <div class="bar"></div>
                <div class="bar"></div>
            </div>
            
            <button id="startBtn" class="btn" onclick="startConversation()">
                🎙️ 대화 시작하기
            </button>
            
            <button id="stopBtn" class="btn stop" onclick="stopConversation()" style="display: none;">
                🛑 대화 종료
            </button>
            
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
        
        <script>
            let ws = null;
            let mediaRecorder = null;
            let audioContext = null;
            let audioStream = null;
            let recognition = null;
            let isUserSpeaking = false;
            let currentUserMessage = '';
            let assistantResponseStarted = false;
            
            function showStatus(message, type) {
                const status = document.getElementById('status');
                status.textContent = message;
                status.className = 'status ' + type;
                status.style.display = 'block';
            }
            
            function hideStatus() {
                document.getElementById('status').style.display = 'none';
            }
            
            function addChatMessage(speaker, message) {
                const chatHistory = document.getElementById('chatHistory');
                const chatContainer = document.getElementById('chatContainer');
                
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
                chatContainer.classList.add('active');
                
                // 스크롤을 맨 아래로
                chatHistory.scrollTop = chatHistory.scrollHeight;
            }
            
            function clearChat() {
                const chatHistory = document.getElementById('chatHistory');
                const chatContainer = document.getElementById('chatContainer');
                chatHistory.innerHTML = '';
                chatContainer.classList.remove('active');
            }
            
            function initSpeechRecognition() {
                // Web Speech API 지원 확인
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) {
                    console.log('Speech Recognition not supported');
                    return null;
                }
                
                recognition = new SpeechRecognition();
                recognition.lang = 'ko-KR';
                recognition.continuous = true;
                recognition.interimResults = true;
                
                recognition.onresult = (event) => {
                    let interimTranscript = '';
                    let finalTranscript = '';
                    
                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        const transcript = event.results[i][0].transcript;
                        if (event.results[i].isFinal) {
                            finalTranscript += transcript;
                        } else {
                            interimTranscript += transcript;
                        }
                    }
                    
                    if (finalTranscript) {
                        addChatMessage('user', finalTranscript);
                        currentUserMessage = '';
                        isUserSpeaking = false;
                        
                        // 어시스턴트 응답 대기 표시
                        setTimeout(() => {
                            if (!assistantResponseStarted) {
                                assistantResponseStarted = true;
                            }
                        }, 500);
                    }
                };
                
                recognition.onerror = (event) => {
                    console.error('Speech recognition error:', event.error);
                };
                
                return recognition;
            }
            
            async function startConversation() {
                try {
                    // 브라우저 호환성 체크
                    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                        showStatus('이 브라우저는 마이크 접근을 지원하지 않습니다. Chrome, Firefox, Safari 최신 버전을 사용해주세요.', 'error');
                        return;
                    }
                    
                    // HTTPS 체크 (localhost 제외)
                    if (window.location.protocol !== 'https:' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
                        showStatus('보안을 위해 HTTPS 연결이 필요합니다. localhost에서 테스트해주세요.', 'error');
                        return;
                    }
                    
                    showStatus('마이크 권한을 요청하고 있습니다...', 'info');
                    
                    // 마이크 접근 권한 요청
                    audioStream = await navigator.mediaDevices.getUserMedia({ 
                        audio: {
                            echoCancellation: true,
                            noiseSuppression: true,
                            autoGainControl: true
                        } 
                    });
                    
                    showStatus('서버에 연결하고 있습니다...', 'info');
                    
                    // WebSocket 연결
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
                    
                    ws.onopen = () => {
                        showStatus('🎤 연결되었습니다! 말씀해 주세요.', 'recording');
                        document.getElementById('audioVisualizer').classList.add('active');
                        document.getElementById('startBtn').style.display = 'none';
                        document.getElementById('stopBtn').style.display = 'block';
                        clearChat();
                        
                        // 초기 인사말 추가
                        addChatMessage('assistant', '안녕하세요! 올리브영 쇼핑 어시스턴트입니다. 매장 정보나 제품 추천이 필요하시면 말씀해 주세요.');
                        
                        // Web Speech API 시작 (대화 내용 표시용)
                        recognition = initSpeechRecognition();
                        if (recognition) {
                            try {
                                recognition.start();
                            } catch (e) {
                                console.log('Recognition already started');
                            }
                        }
                        
                        // MediaRecorder 시작 (실제 음성 전송용)
                        mediaRecorder = new MediaRecorder(audioStream, {
                            mimeType: 'audio/webm'
                        });
                        
                        mediaRecorder.ondataavailable = (event) => {
                            if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
                                ws.send(event.data);
                            }
                        };
                        
                        mediaRecorder.start(100); // 100ms마다 데이터 전송
                    };
                    
                    ws.onmessage = async (event) => {
                        // JSON 메시지 처리 (텍스트)
                        if (typeof event.data === 'string') {
                            try {
                                const data = JSON.parse(event.data);
                                if (data.type === 'transcript') {
                                    // 사용자 음성 인식 결과
                                    if (data.text && data.text.trim()) {
                                        addChatMessage('user', data.text);
                                    }
                                } else if (data.type === 'response') {
                                    // 어시스턴트 응답 텍스트
                                    if (data.text && data.text.trim()) {
                                        addChatMessage('assistant', data.text);
                                    }
                                }
                            } catch (e) {
                                console.log('Non-JSON message:', event.data);
                            }
                        }
                        // Blob 메시지 처리 (오디오)
                        else if (event.data instanceof Blob) {
                            // 첫 오디오 응답이 올 때 어시스턴트 메시지 표시
                            if (assistantResponseStarted) {
                                addChatMessage('assistant', '🔊 음성으로 응답 중...');
                                assistantResponseStarted = false;
                            }
                            playAudio(event.data);
                        }
                    };
                    
                    ws.onerror = (error) => {
                        console.error('WebSocket error:', error);
                        showStatus('연결 오류가 발생했습니다.', 'error');
                    };
                    
                    ws.onclose = () => {
                        showStatus('연결이 종료되었습니다.', 'info');
                        cleanup();
                    };
                    
                } catch (error) {
                    console.error('Error:', error);
                    if (error.name === 'NotAllowedError') {
                        showStatus('마이크 권한이 거부되었습니다. 브라우저 설정에서 마이크를 허용해주세요.', 'error');
                    } else if (error.name === 'NotFoundError') {
                        showStatus('마이크를 찾을 수 없습니다. 마이크가 연결되어 있는지 확인해주세요.', 'error');
                    } else if (error.name === 'NotReadableError') {
                        showStatus('마이크가 다른 앱에서 사용 중입니다. 다른 앱을 종료해주세요.', 'error');
                    } else if (error.name === 'TypeError') {
                        showStatus('브라우저가 마이크 접근을 지원하지 않습니다. Chrome, Firefox, Safari 최신 버전을 사용해주세요.', 'error');
                    } else {
                        showStatus('오류가 발생했습니다: ' + error.message, 'error');
                    }
                    cleanup();
                }
            }
            
            function stopConversation() {
                if (ws) {
                    ws.close();
                }
                cleanup();
                showStatus('대화가 종료되었습니다.', 'info');
            }
            
            function cleanup() {
                if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                    mediaRecorder.stop();
                }
                
                if (audioStream) {
                    audioStream.getTracks().forEach(track => track.stop());
                    audioStream = null;
                }
                
                if (recognition) {
                    try {
                        recognition.stop();
                    } catch (e) {
                        console.log('Recognition already stopped');
                    }
                    recognition = null;
                }
                
                document.getElementById('audioVisualizer').classList.remove('active');
                document.getElementById('startBtn').style.display = 'block';
                document.getElementById('stopBtn').style.display = 'none';
                
                mediaRecorder = null;
                ws = null;
                isUserSpeaking = false;
                currentUserMessage = '';
                assistantResponseStarted = false;
            }
            
            async function playAudio(audioBlob) {
                const audioUrl = URL.createObjectURL(audioBlob);
                const audio = new Audio(audioUrl);
                
                try {
                    await audio.play();
                } catch (error) {
                    console.error('Error playing audio:', error);
                }
                
                audio.onended = () => {
                    URL.revokeObjectURL(audioUrl);
                };
            }
            
            // 페이지 언로드 시 정리
            window.addEventListener('beforeunload', cleanup);
            
            // 페이지 로드 시 브라우저 호환성 체크
            window.addEventListener('DOMContentLoaded', () => {
                if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                    showStatus('⚠️ 이 브라우저는 마이크 접근을 지원하지 않습니다. Chrome, Firefox, Safari 최신 버전을 사용해주세요.', 'error');
                    document.getElementById('startBtn').disabled = true;
                } else if (window.location.protocol !== 'https:' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
                    showStatus('⚠️ HTTPS 연결이 필요합니다. localhost에서 테스트해주세요.', 'error');
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 엔드포인트 - 음성 챗봇 연결
    """
    await websocket.accept()
    logger.info("WebSocket connection accepted")
    
    try:
        # 봇 인스턴스 생성
        bot = OliveYoungVoiceBot()
        
        # Transport 파라미터 생성
        transport_params = bot.create_transport_params()
        
        # Transport 생성
        transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=transport_params
        )
        
        # 봇 실행
        await bot.run_bot(transport)
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {e}")
        await websocket.close()


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
