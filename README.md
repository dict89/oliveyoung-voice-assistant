# 🛍️ 올리브영 음성 쇼핑 어시스턴트

**Pipecat** 프레임워크를 활용한 실시간 음성 대화형 올리브영 매장 정보 제공 서비스입니다.

참고: [Pipecat 예제](https://github.com/pipecat-ai/pipecat/blob/main/examples/foundational/38-smart-turn-fal.py)

## ✨ 주요 기능

- 🎙️ **실시간 음성 대화**: Speech-to-Speech로 자연스러운 대화
- 🏪 **매장 정보 제공**: 위치, 영업시간, 연락처, 서비스 안내
- 🗺️ **교통 안내**: 가까운 지하철역 및 주변 랜드마크 정보
- 🔥 **제품 추천**: 인기 상품 및 브랜드 정보 제공
- 🌐 **웹 인터페이스**: 브라우저에서 바로 사용 가능
- 🗺️ **매장 내 위치 지도**: 추천 제품 클릭 시 매장 내 위치 확인

## 🛠️ 기술 스택

- **Pipecat**: 실시간 음성 대화 프레임워크
- **ElevenLabs Scribe Realtime v2**: STT (Speech-to-Text) - 초저지연 음성 인식
- **Cartesia**: TTS (Text-to-Speech)
- **OpenAI GPT-4**: LLM (Large Language Model)
- **Daily.co**: WebRTC 오디오 통신
- **FastAPI**: 백엔드 API 서버
- **Python 3.10+**

## 📋 사전 요구사항

1. **Python 3.10 이상**
2. **OpenAI API Key**: [OpenAI](https://platform.openai.com/api-keys)에서 발급
3. **Cartesia API Key**: [Cartesia](https://cartesia.ai/)에서 발급
4. **ElevenLabs API Key**: [ElevenLabs](https://elevenlabs.io/app/settings/api-keys)에서 발급
5. **Daily.co API Key**: [Daily.co](https://dashboard.daily.co/)에서 발급

## 🚀 설치 및 실행

### 1. 저장소 클론 (또는 프로젝트 디렉토리로 이동)

```bash
cd /Users/uijungchung/pipecat
```

### 2. UV 설치 (Python 패키지 매니저)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. 의존성 설치

```bash
uv sync
```

### 4. 환경 변수 설정

`.env` 파일을 생성하고 API 키를 입력하세요:

```bash
cp .env.example .env
```

`.env` 파일 내용:
```
OPENAI_API_KEY=your_openai_api_key_here
CARTESIA_API_KEY=your_cartesia_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
DAILY_API_KEY=your_daily_api_key_here
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

### 5. 서버 실행

```bash
uv run python -m src.server
```

또는:

```bash
uv run uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
```

또는 실행 스크립트 사용:

```bash
./run.sh
```

### 6. 웹 브라우저에서 접속

```
http://localhost:8000
```

## 📖 사용 방법

### 웹 인터페이스 사용

1. 브라우저에서 `http://localhost:8000` 접속
2. "대화 시작하기" 버튼 클릭
3. 마이크 권한 허용
4. AI 어시스턴트와 음성으로 대화 시작

### 질문 예시

- "강남역 근처 올리브영 어디 있어요?"
- "명동점 영업시간 알려주세요"
- "홍대 매장에서 피부 진단 서비스 있나요?"
- "인기 있는 스킨케어 제품 추천해주세요"
- "잠실 롯데월드 근처 매장 있나요?"

## 📁 프로젝트 구조

```
pipecat/
├── src/
│   ├── __init__.py
│   ├── bot.py                  # Pipecat 봇 메인 로직
│   ├── server.py               # FastAPI 서버 + WebSocket
│   ├── store_service.py        # 매장 정보 서비스
│   └── oliveyoung_crawler.py   # 올리브영 크롤러 (NEW!)
├── data/
│   └── store_data.json         # 매장 데이터
├── tests/
│   ├── test_store_service.py
│   └── test_oliveyoung_crawler.py  # 크롤러 테스트 (NEW!)
├── crawl.py                    # 크롤러 실행 스크립트 (NEW!)
├── debug_crawler.py            # 크롤러 디버깅 도구 (NEW!)
├── pyproject.toml              # 프로젝트 설정 및 의존성
├── requirements.txt            # pip 의존성
├── .env.example                # 환경 변수 예시
├── run.sh                      # 실행 스크립트
├── CRAWLER_QUICKSTART.md       # 크롤러 빠른 시작 가이드 (NEW!)
├── CRAWLER_GUIDE.md            # 크롤러 상세 가이드 (NEW!)
└── README.md
```

## 🔧 아키텍처

### WebSocket 기반 실시간 통신

```
┌─────────────────┐
│   Web Browser   │
│   (User UI)     │
└────────┬────────┘
         │ WebSocket
         ↓
┌─────────────────────────────────────────┐
│         Pipecat Pipeline                │
├─────────────────────────────────────────┤
│  Audio Input                            │
│    ↓                                    │
│  VAD (Silero - Voice Activity Detection)│
│    ↓                                    │
│  STT (Cartesia - Speech-to-Text)        │
│    ↓                                    │
│  LLM (GPT-4 - Language Model)           │
│    ↓                                    │
│  TTS (Cartesia - Text-to-Speech)        │
│    ↓                                    │
│  Audio Output                           │
└────────┬────────────────────────────────┘
         │
         ↓
┌─────────────────┐
│  Store Service  │
│  (Data Layer)   │
└─────────────────┘
```

### 파이프라인 구성 (bot.py)

```python
Pipeline([
    transport.input(),           # WebSocket 오디오 입력
    stt,                         # Cartesia STT
    context_aggregator.user(),   # 사용자 메시지 집계
    llm,                         # OpenAI GPT-4
    tts,                         # Cartesia TTS
    transport.output(),          # WebSocket 오디오 출력
    context_aggregator.assistant() # 어시스턴트 응답 집계
])
```

## 🔧 설정 옵션

### 음성 설정 (bot.py)

```python
# Cartesia TTS 음성 변경
tts = CartesiaTTSService(
    api_key=self.cartesia_api_key,
    voice_id="a167e0f3-df7e-4d52-a9c3-f949145efdab",  # 한국어 음성
)

# LLM 모델 변경
llm = OpenAILLMService(
    model="gpt-4o-mini"  # 또는 "gpt-4o" (더 높은 품질)
)

# VAD 민감도 조정
vad_analyzer=SileroVADAnalyzer(
    params=VADParams(stop_secs=0.2)  # 침묵 감지 시간
)
```

## 📊 매장 및 상품 데이터

### 매장 데이터 추가

`data/store_data.json` 파일에서 매장 정보를 수동으로 추가/수정할 수 있습니다:

```json
{
  "stores": [
    {
      "store_id": "D176",
      "name": "올리브영 강남역점",
      "address": "서울특별시 강남구 강남대로 지하396",
      "phone": "02-123-4567",
      "operating_hours": {
        "weekday": "10:00 - 22:00",
        "weekend": "10:00 - 22:00"
      },
      ...
    }
  ]
}
```

### 🕷️ 올리브영 상품 데이터 수집 (NEW!)

올리브영 상품 정보(사진, 이름, 가격, 재고)를 수집하는 세 가지 방법을 제공합니다.

#### 방법 1: 샘플 데이터 사용 ⭐ (추천)

개발/테스트용으로 24개 실제 상품 샘플 데이터를 제공합니다:

```bash
# 샘플 데이터 확인
cat data/sample_products.json | python3 -m json.tool | head -50

# Python에서 사용
python3
>>> import json
>>> with open('data/sample_products.json', 'r', encoding='utf-8') as f:
>>>     data = json.load(f)
>>> print(f"총 {data['total_products']}개 상품")
```

- 📖 [샘플 데이터 활용 가이드](USE_SAMPLE_DATA.md)

#### 방법 2: 크롬 개발자 도구로 수동 추출 ⭐⭐ (실전 추천)

브라우저에서 직접 데이터를 추출하는 가장 확실한 방법:

```bash
# 1. 올리브영 웹사이트 접속
# 2. F12 → Console 탭
# 3. JavaScript 스크립트 실행하여 데이터 추출
# 4. 클립보드에서 JSON 파일로 저장

# 추출한 데이터 변환
python3 convert_manual_data.py data/raw_skincare.json data/skincare.json

# 여러 카테고리 병합
python3 convert_manual_data.py --merge \
  data/skincare.json \
  data/makeup.json \
  data/all_products.json
```

- 📖 [수동 추출 완벽 가이드](MANUAL_SCRAPING_GUIDE.md) - F12로 데이터 추출하기

#### 방법 3: 자동 크롤러 (고급/실험적)

자동화된 크롤링 (올리브영 웹사이트의 복잡한 구조로 인해 제한적):

```bash
# 크롤링 의존성 설치
pip install playwright beautifulsoup4 lxml
playwright install chromium

# 크롤러 실행
python3 crawl_oliveyoung.py "명동 타운"
```

- 📚 [자동 크롤러 가이드](CRAWLER_GUIDE.md)

#### 크롤링 결과 형식

```json
{
  "store_name": "올리브영 명동 타운",
  "crawled_at": "2025-11-10T14:30:00",
  "categories": {
    "스킨케어": [
      {
        "product_id": "A000123",
        "name": "토리든 다이브인 세럼",
        "brand": "토리든",
        "price": 25000,
        "image_url": "https://image.oliveyoung.co.kr/...",
        "stock_status": "재고있음"
      }
    ]
  }
}
```

## 🐛 트러블슈팅

### 1. "OPENAI_API_KEY가 설정되지 않았습니다" 오류

- `.env` 파일이 프로젝트 루트에 있는지 확인
- API 키가 올바르게 입력되었는지 확인

### 2. "CARTESIA_API_KEY가 설정되지 않았습니다" 오류

- Cartesia API 키가 `.env` 파일에 있는지 확인
- [Cartesia](https://cartesia.ai/)에서 API 키 발급

### 3. WebSocket 연결 오류

- 서버가 실행 중인지 확인
- 브라우저 콘솔에서 오류 메시지 확인
- 포트 8000이 사용 가능한지 확인

### 4. 마이크 권한 오류

- 브라우저 설정에서 마이크 권한 허용
- HTTPS 연결 사용 (로컬에서는 localhost 허용됨)

### 5. 음성 인식이 잘 안 됨

- 마이크 품질 확인
- 주변 소음 줄이기
- VAD 파라미터 조정 (`stop_secs` 값 변경)

## 🔐 보안 고려사항

- `.env` 파일을 Git에 커밋하지 마세요
- API 키는 환경 변수로만 관리하세요
- 프로덕션 환경에서는 HTTPS 사용 필수
- WebSocket 연결에 인증 추가 고려

## 📚 참고 자료

- [Pipecat Documentation](https://docs.pipecat.ai/)
- [Pipecat GitHub](https://github.com/pipecat-ai/pipecat)
- [Pipecat Example: Smart Turn](https://github.com/pipecat-ai/pipecat/blob/main/examples/foundational/38-smart-turn-fal.py)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Cartesia Documentation](https://docs.cartesia.ai/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 🤝 기여

기여를 환영합니다! 이슈나 PR을 자유롭게 제출해주세요.

## 📝 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

## 💬 문의

질문이나 제안사항이 있으시면 이슈를 등록해주세요.

---

**Made with ❤️ using [Pipecat](https://github.com/pipecat-ai/pipecat)**
