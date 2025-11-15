# ElevenLabs STT 403 에러 해결 가이드

## 🔴 현재 문제
- **에러**: HTTP 403 Forbidden
- **발생 시점**: WebSocket 연결 시
- **토큰 생성**: 성공 (HTTP 200)
- **WebSocket 연결**: 실패 (HTTP 403)

## 🔍 가능한 원인

### 1. API 키 권한 문제
- **원인**: API 키가 Scribe Realtime v2에 접근할 수 없음
- **해결**: 
  - ElevenLabs 대시보드에서 API 키 확인
  - https://elevenlabs.io/app/settings/api-keys
  - 새 API 키 생성 시도

### 2. 계정 플랜 제한
- **원인**: Scribe Realtime v2는 유료 플랜이 필요할 수 있음
- **해결**:
  - ElevenLabs 계정 확인
  - https://elevenlabs.io/app/settings/billing
  - 유료 플랜 필요 여부 확인

### 3. WebSocket URL 형식 오류
- **원인**: WebSocket URL이나 토큰 전달 방식이 잘못됨
- **현재 URL**: `wss://api.elevenlabs.io/v1/speech-to-text/realtime/websocket?token={token}`
- **해결**: 
  - ElevenLabs 문서 재확인
  - https://elevenlabs.io/docs/cookbooks/speech-to-text/streaming

### 4. 토큰 만료
- **원인**: 토큰이 만료되었거나 무효함
- **해결**: 
  - 토큰 생성 후 즉시 사용
  - 토큰 생성 시간 확인

## 🛠️ 진단 방법

### 1. API 키 확인
```bash
# .env 파일 확인
cat .env | grep ELEVENLABS_API_KEY
```

### 2. 토큰 생성 테스트
```bash
# 진단 스크립트 실행
python3 debug_elevenlabs.py
```

### 3. 로그 확인
서버 실행 시 다음 로그를 확인:
- `📡 Token generation response status: 200` (성공)
- `📝 Token length: XX` (토큰 길이)
- `❌ ElevenLabs STT connection error: HTTP 403` (에러)

## 💡 해결 방법

### 방법 1: API 키 재생성
1. ElevenLabs 대시보드 접속
2. API Keys 페이지로 이동
3. 새 API 키 생성
4. `.env` 파일에 업데이트

### 방법 2: 계정 플랜 확인
1. ElevenLabs 계정 설정 확인
2. Billing 페이지 확인
3. Scribe Realtime v2 접근 권한 확인
4. 필요 시 플랜 업그레이드

### 방법 3: Python SDK 사용
ElevenLabs Python SDK를 사용하면 인증이 자동으로 처리됩니다.

### 방법 4: OpenAI Whisper로 대체
일시적으로 OpenAI Whisper를 사용할 수 있습니다 (한국어 인식 우수).

## 📝 확인 사항

1. ✅ `.env` 파일에 `ELEVENLABS_API_KEY`가 설정되어 있는가?
2. ✅ API 키가 올바른 형식인가? (길이, 형식 확인)
3. ✅ ElevenLabs 계정이 활성화되어 있는가?
4. ✅ 계정이 Scribe Realtime v2에 접근할 수 있는가?
5. ✅ 유료 플랜이 필요한가?

## 🔗 유용한 링크

- ElevenLabs API 문서: https://elevenlabs.io/docs/api-reference
- Scribe Realtime v2 가이드: https://elevenlabs.io/docs/cookbooks/speech-to-text/streaming
- ElevenLabs 대시보드: https://elevenlabs.io/app/settings/api-keys
- 지원팀 문의: https://elevenlabs.io/support

