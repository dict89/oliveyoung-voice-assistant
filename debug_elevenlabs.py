#!/usr/bin/env python3
"""
ElevenLabs 연결 진단 스크립트
토큰 생성 및 WebSocket 연결을 테스트합니다.
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

async def test_elevenlabs_connection():
    """ElevenLabs 연결 테스트"""
    import aiohttp
    import websockets
    
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("❌ ELEVENLABS_API_KEY가 설정되지 않았습니다.")
        print("💡 .env 파일에 ELEVENLABS_API_KEY를 추가하세요.")
        return
    
    print("=" * 60)
    print("ElevenLabs 연결 진단")
    print("=" * 60)
    print(f"📝 API Key length: {len(api_key)}")
    print(f"📝 API Key prefix: {api_key[:15]}...")
    print()
    
    # 1. 토큰 생성 테스트
    print("1️⃣ 토큰 생성 테스트...")
    token = None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.elevenlabs.io/v1/single-use-token/realtime_scribe",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                },
            ) as response:
                print(f"   📡 Response status: {response.status}")
                print(f"   📡 Response headers: {dict(response.headers)}")
                
                if response.status != 200:
                    error_text = await response.text()
                    print(f"   ❌ Error: {error_text}")
                    print()
                    print("💡 가능한 원인:")
                    if response.status == 401:
                        print("   - API 키가 잘못되었습니다")
                        print("   - .env 파일의 ELEVENLABS_API_KEY를 확인하세요")
                    elif response.status == 403:
                        print("   - API 키에 Scribe Realtime v2 접근 권한이 없습니다")
                        print("   - ElevenLabs 계정이 유료 플랜이 필요할 수 있습니다")
                        print("   - https://elevenlabs.io 에서 계정 상태를 확인하세요")
                    elif response.status == 429:
                        print("   - Rate limit 초과")
                        print("   - 잠시 후 다시 시도하세요")
                    return
                
                data = await response.json()
                print(f"   📝 Response data: {data}")
                
                token = data.get("token")
                if token:
                    print(f"   ✅ Token generated successfully")
                    print(f"   📝 Token length: {len(token)}")
                    print(f"   📝 Token prefix: {token[:20]}...")
                else:
                    print(f"   ❌ Token not found in response")
                    print(f"   📝 Available fields: {list(data.keys())}")
                    return
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    if not token:
        print("   ❌ Token generation failed")
        return
    
    print()
    
    # 2. WebSocket 연결 테스트
    print("2️⃣ WebSocket 연결 테스트...")
    base_url = "wss://api.elevenlabs.io/v1/speech-to-text/realtime/websocket"
    
    # 여러 URL 형식 시도
    url_formats = [
        f"{base_url}?token={token}",  # URL 인코딩 없이
        f"{base_url}?token={token}&language=ko",  # 언어 포함
    ]
    
    for i, url in enumerate(url_formats, 1):
        print(f"   📡 Trying URL format {i}: {base_url}?token=<TOKEN>")
        try:
            async with websockets.connect(url) as websocket:
                print(f"   ✅ WebSocket connection successful!")
                
                # 첫 메시지 수신 대기
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f"   📨 Received message: {message}")
                    print()
                    print("✅ 모든 테스트 통과!")
                    return True
                except asyncio.TimeoutError:
                    print(f"   ⚠️ No message received within 5 seconds")
                    print(f"   💡 Connection may still be valid")
                    return True
                    
        except websockets.exceptions.InvalidStatusCode as e:
            print(f"   ❌ HTTP {e.status_code}: Connection failed")
            if e.status_code == 403:
                print(f"   💡 HTTP 403: Authentication failed")
                print(f"   💡 Possible causes:")
                print(f"      - Token is invalid or expired")
                print(f"      - API key does not have access to Scribe Realtime v2")
                print(f"      - Scribe Realtime v2 requires a paid plan")
                print(f"      - WebSocket URL format is incorrect")
            continue
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue
    
    print()
    print("❌ 모든 WebSocket 연결 시도 실패")
    print()
    print("💡 해결 방법:")
    print("   1. ElevenLabs 대시보드에서 API 키 확인")
    print("   2. 계정이 Scribe Realtime v2에 접근할 수 있는지 확인")
    print("   3. 유료 플랜이 필요한지 확인")
    print("   4. ElevenLabs 지원팀에 문의")
    
    return False

if __name__ == "__main__":
    asyncio.run(test_elevenlabs_connection())

