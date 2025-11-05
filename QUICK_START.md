# 🚀 빠른 시작 가이드

올리브영 음성 쇼핑 어시스턴트를 5분 안에 시작하세요!

## 1️⃣ API 키 발급받기

### OpenAI API Key
1. [OpenAI 플랫폼](https://platform.openai.com/api-keys) 접속
2. "Create new secret key" 클릭
3. 키 복사 (다시 볼 수 없으니 안전한 곳에 저장!)

### Cartesia API Key
1. [Cartesia](https://cartesia.ai/) 접속
2. 회원가입 및 로그인
3. API Keys 페이지에서 키 생성
4. API Key 복사

## 2️⃣ 프로젝트 설정

### UV 설치 (Python 패키지 매니저)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 환경 변수 설정
```bash
# .env 파일 생성
cp .env.example .env

# 편집기로 .env 파일을 열어 API 키 입력
nano .env
```

`.env` 파일 내용:
```
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
CARTESIA_API_KEY=xxxxxxxxxxxxx
HOST=0.0.0.0
PORT=8000
```

## 3️⃣ 실행

### 방법 1: 쉘 스크립트 사용 (권장)
```bash
chmod +x run.sh
./run.sh
```

### 방법 2: 직접 실행
```bash
# 의존성 설치
uv sync

# 서버 실행
uv run python -m src.server
```

### 방법 3: pip 사용 (UV 없이)
```bash
pip install -r requirements.txt
python -m src.server
```

## 4️⃣ 브라우저에서 접속

```
http://localhost:8000
```

"대화 시작하기" 버튼을 클릭하고 마이크 권한을 허용하세요!

## 🎤 대화 예시

- "강남역 근처 올리브영 어디 있어요?"
- "명동점 영업시간 알려주세요"
- "홍대 매장에 주차 가능한가요?"
- "인기 있는 스킨케어 제품 추천해주세요"

## ⚙️ 기술 스택

| 구성요소 | 기술 |
|---------|------|
| Framework | Pipecat |
| STT | Cartesia |
| TTS | Cartesia |
| LLM | OpenAI GPT-4 |
| Transport | WebSocket |
| Backend | FastAPI |

## ⚠️ 문제 해결

### "OPENAI_API_KEY가 설정되지 않았습니다"
→ `.env` 파일이 프로젝트 루트에 있는지 확인하고 API 키를 입력했는지 확인하세요.

### "CARTESIA_API_KEY가 설정되지 않았습니다"
→ `.env` 파일에 Cartesia API 키를 입력했는지 확인하세요.

### "UV가 설치되어 있지 않습니다"
→ UV 설치 명령어를 실행하고 터미널을 재시작하세요.

### 마이크가 작동하지 않습니다
→ 브라우저 설정에서 마이크 권한을 허용했는지 확인하세요.

### WebSocket 연결 오류
→ 서버가 실행 중인지 확인하고, 브라우저 콘솔에서 오류 메시지를 확인하세요.

## 🔍 차이점: Daily.co vs WebSocket

이 프로젝트는 **Daily.co 대신 WebSocket**을 사용합니다:

| 구분 | Daily.co | WebSocket |
|------|----------|-----------|
| 설정 복잡도 | 높음 (API 키, 룸 생성) | 낮음 (서버만 실행) |
| 외부 의존성 | 있음 (Daily.co 서비스) | 없음 (자체 서버) |
| 비용 | 사용량 기반 과금 | 무료 (서버 비용만) |
| 확장성 | 높음 | 중간 |
| 사용 사례 | 프로덕션, 멀티룸 | 개발, 단일 세션 |

## 💡 팁

- 첫 실행 시 의존성 설치에 약 1-2분 소요됩니다
- 마이크 품질이 좋을수록 인식률이 높습니다
- 조용한 환경에서 사용하세요
- 한 번에 한 명씩 대화하세요

## 📚 더 알아보기

- [전체 문서 보기](README.md)
- [아키텍처 문서](ARCHITECTURE.md)
- [Pipecat 문서](https://docs.pipecat.ai/)
- [매장 데이터 수정하기](data/store_data.json)

---

**문제가 해결되지 않나요?** GitHub Issues에 질문을 남겨주세요!
