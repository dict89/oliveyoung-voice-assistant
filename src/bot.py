"""
올리브영 음성 쇼핑 어시스턴트 봇
Pipecat을 사용한 실시간 음성 대화 구현 (Daily.co Transport)
"""
import asyncio
import os
import sys

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import (
    EndFrame,
    TranscriptionFrame,
    TextFrame,
    Frame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response import (
    LLMAssistantResponseAggregator,
    LLMUserResponseAggregator,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.openai.stt import OpenAISTTService
from pipecat.transports.daily.transport import DailyParams, DailyTransport

from loguru import logger
from dotenv import load_dotenv

from .store_service import StoreService
from .websocket_manager import broadcast_message

# 환경 변수 로드
load_dotenv()

# 로거 설정
logger.remove(0)
logger.add(sys.stderr, level="INFO")


class IntentDetectionFilter(FrameProcessor):
    """하이브리드 의도 판단 필터: 빠른 키워드 체크 + LLM 백업"""
    
    # 확실한 YES 키워드 (즉시 통과)
    DEFINITE_YES_KEYWORDS = [
        "안녕", "추천", "알려", "찾아", "도와", "질문", "문의",
        "어디", "위치", "매장", "제품", "영업", "시간", "연락",
        "hello", "hi", "hey", "help", "recommend", "where", "store",
        "product", "location", "contact", "popular", "인기"
    ]
    
    # 확실한 NO 패턴 (즉시 차단)
    DEFINITE_NO_PATTERNS = [
        "mbc 뉴스", "kbs", "sbs", "자막", "구독", "좋아요",
        "시청", "감사합니다", "수고", "잘 먹겠습니다"
    ]
    
    def __init__(self, openai_api_key: str):
        super().__init__()
        self.openai_api_key = openai_api_key
        
        # 판단용 LLM (불명확한 경우만 사용)
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=openai_api_key)
        
        self.intent_prompt = """You are an intent classifier for an AI shopping assistant.

Respond with ONLY one word: "YES" or "NO"

YES = User is talking to the AI assistant (asking questions, requesting help)
NO = User is having a side conversation or not addressing the assistant

User input: "{text}"

Your answer (YES or NO):"""
    
    def _quick_keyword_check(self, text: str) -> str:
        """빠른 키워드 체크 (밀리초 단위)
        
        Returns:
            "YES" - 확실히 AI에게 하는 말
            "NO" - 확실히 AI에게 하는 말이 아님
            "UNCLEAR" - 불명확, LLM 판단 필요
        """
        text_lower = text.lower()
        
        # 1. 확실한 NO 패턴 체크 (가장 먼저)
        for pattern in self.DEFINITE_NO_PATTERNS:
            if pattern in text_lower:
                return "NO"
        
        # 2. 확실한 YES 키워드 체크
        for keyword in self.DEFINITE_YES_KEYWORDS:
            if keyword in text_lower:
                return "YES"
        
        # 3. 매우 짧은 문장은 보통 AI에게 하는 말이 아님
        if len(text.strip()) < 5:
            return "NO"
        
        # 4. 불명확한 경우 (LLM 필요)
        return "UNCLEAR"
    
    async def _check_intent_with_llm(self, text: str) -> bool:
        """LLM으로 의도 판단 (불명확한 경우만 호출)"""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": self.intent_prompt.format(text=text)}
                ],
                temperature=0,
                max_tokens=5
            )
            
            answer = response.choices[0].message.content.strip().upper()
            return answer == "YES"
            
        except Exception as e:
            logger.error(f"❌ Intent detection error: {e}")
            return True  # 오류 시 통과
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        # TranscriptionFrame만 필터링
        if isinstance(frame, TranscriptionFrame):
            text = frame.text
            
            if text and text.strip() and len(text.strip()) > 1:
                # Step 1: 빠른 키워드 체크 (밀리초)
                quick_result = self._quick_keyword_check(text)
                
                if quick_result == "YES":
                    logger.info(f"✅ [KEYWORD: YES] Fast pass: {text}")
                    await self.push_frame(frame, direction)
                    return
                elif quick_result == "NO":
                    logger.info(f"⏭️ [KEYWORD: NO] Fast reject: {text}")
                    return
                else:
                    # Step 2: 불명확한 경우만 LLM 사용
                    logger.info(f"🤔 [UNCLEAR] Checking with LLM: {text}")
                    should_respond = await self._check_intent_with_llm(text)
                    
                    if should_respond:
                        logger.info(f"✅ [LLM: YES] Forwarding to LLM: {text}")
                        await self.push_frame(frame, direction)
                    else:
                        logger.info(f"⏭️ [LLM: NO] Ignoring: {text}")
            else:
                return
        else:
            # 다른 프레임은 그대로 전달
            await self.push_frame(frame, direction)


class TranscriptLogger(FrameProcessor):
    """대화 내용을 WebSocket으로 전송하는 프로세서 (Intent:YES만 도달)"""
    
    def __init__(self):
        super().__init__()
        # StoreService 인스턴스 (제품/매장 정보 조회용)
        from .store_service import StoreService
        self.store_service = StoreService()
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        # STT 결과 (사용자 음성 인식) - Intent:YES인 것만 여기 도달
        if isinstance(frame, TranscriptionFrame):
            text = frame.text
            # 빈 문자열이나 공백만 있는 경우 무시
            if text and text.strip() and len(text.strip()) > 1:
                # 브라우저 채팅창으로만 전송 (로그는 IntentDetectionFilter에서 이미 출력)
                await broadcast_message({
                    "type": "transcript",
                    "speaker": "user",
                    "text": text.strip()  # 공백 제거
                })
        
        # LLM 응답 텍스트
        elif isinstance(frame, TextFrame):
            text = frame.text
            if text and text.strip():
                logger.info(f"🤖 [ASSISTANT]: {text}")
                
                # [PRODUCTS:...] 패턴 파싱
                import re
                products_match = re.search(r'\[PRODUCTS:(.*?)\]', text)
                if products_match:
                    product_ids = [pid.strip() for pid in products_match.group(1).split(',')]
                    logger.info(f"🛍️ Found product IDs: {product_ids}")
                    
                    # 제품 정보 조회
                    all_products = self.store_service.get_all_products()
                    selected_products = [
                        p for p in all_products 
                        if p.get('product_id') in product_ids
                    ]
                    
                    if selected_products:
                        # 이미지 표시 메시지 전송
                        await broadcast_message({
                            "type": "show_images",
                            "content_type": "products",
                            "data": {"products": selected_products}
                        })
                        logger.info(f"✅ Sent product images: {len(selected_products)} items")
                    
                    # 텍스트에서 태그 제거 (TTS용)
                    text = re.sub(r'\[PRODUCTS:.*?\]', '', text).strip()
                
                # [STORE:...] 패턴 파싱
                store_match = re.search(r'\[STORE:(.*?)\]', text)
                if store_match:
                    store_id = store_match.group(1).strip()
                    logger.info(f"🏪 Found store ID: {store_id}")
                    
                    # 매장 정보 조회
                    main_store = self.store_service.data.get("store", {})
                    if main_store.get("store_id") == store_id:
                        store_images = main_store.get("store_images", [])
                        if store_images:
                            await broadcast_message({
                                "type": "show_images",
                                "content_type": "store",
                                "data": {
                                    "store_name": main_store.get("store_name", ""),
                                    "image_url": store_images[0],
                                    "address": main_store.get("address", "")
                                }
                            })
                            logger.info(f"✅ Sent store image")
                    
                    # 텍스트에서 태그 제거 (TTS용)
                    text = re.sub(r'\[STORE:.*?\]', '', text).strip()
                
                # 브라우저로 전송 (태그 제거된 텍스트)
                await broadcast_message({
                    "type": "response",
                    "speaker": "assistant",
                    "text": text
                })
        
        await self.push_frame(frame, direction)


class OliveYoungVoiceBot:
    """올리브영 음성 쇼핑 어시스턴트 봇"""
    
    def __init__(self):
        self.store_service = StoreService()
        
        # API 키 확인
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        
        self.cartesia_api_key = os.getenv("CARTESIA_API_KEY")
        if not self.cartesia_api_key:
            raise ValueError("CARTESIA_API_KEY가 설정되지 않았습니다.")
        
        # 시스템 프롬프트 생성
        self.system_prompt = self._create_system_prompt()
    
    def _create_system_prompt(self) -> str:
        """봇의 시스템 프롬프트를 생성합니다."""
        
        # 매장 정보
        main_store = self.store_service.data.get("store", {})
        store_name = main_store.get("store_name", "")
        store_address = main_store.get("address", "")
        store_phone = main_store.get("phone", "")
        subway_info = main_store.get("subway_info", "")
        
        # 인기 제품 (할인율 높은 순 5개, ID 포함)
        popular_products = self.store_service.get_popular_products(limit=5)
        products_summary = "\n".join([
            f"- [{p['product_id']}] {p['name'][:50]}... (할인 {p['discount_rate']}%, {p['sale_price']:,}원)"
            for p in popular_products
        ])
        
        # 카테고리 정보
        categories = self.store_service.get_categories()
        categories_summary = ", ".join(categories.keys())
        
        # 인근 매장 (5개만)
        nearby_stores = self.store_service.data.get("nearby_stores", [])[:5]
        nearby_summary = "\n".join([
            f"- {store.get('name', '')}: {store.get('address', '')}"
            for store in nearby_stores
        ])
        
        prompt = f"""당신은 올리브영(Olive Young)의 친절한 AI 쇼핑 어시스턴트입니다.

[역할]
- 고객에게 올리브영 매장 정보를 안내합니다
- 제품 추천과 쇼핑 관련 질문에 답변합니다
- 항상 친절하고 전문적인 톤으로 응대합니다
- 자연스러운 대화체를 사용합니다

[메인 매장 정보]
매장명: {store_name}
매장ID: D176
주소: {store_address}
전화: {store_phone}
지하철: {subway_info}

[현재 인기 제품 TOP 5]
{products_summary}

[제품 카테고리]
{categories_summary}

[인근 매장 (참고용)]
{nearby_summary}

[이미지 표시 규칙 - 절대 필수!]
**제품 추천 시 응답 마지막에 PRODUCTS 태그를 100% 추가해야 합니다!**
**매장 정보 시 응답 마지막에 STORE 태그를 100% 추가해야 합니다!**

형식:
- 제품: [PRODUCTS:제품ID1,제품ID2,제품ID3]
- 매장: [STORE:매장ID]

필수 예시:
Q: "제품 추천해줘"
A: "토리든 세럼과 달바 세럼 추천드립니다. [PRODUCTS:A000000189261,A000000232724]"

Q: "인기 제품 뭐야?"
A: "에스트라 크림, 토리든 세럼, 달바 세럼이 인기입니다. [PRODUCTS:A000000236338,A000000189261,A000000232724]"

Q: "매장 위치 알려줘"
A: "서울 중구 명동길 53에 있습니다. 명동역 8번 출구입니다. [STORE:D176]"

**태그 없이 답변하면 안 됩니다! 반드시 추가하세요!**

[응대 가이드라인]
1. 고객의 질문을 정확히 이해하고 관련 정보를 제공하세요
2. 매장 위치를 물으면 주소와 지하철 정보를 안내하세요
3. 영업시간, 전화번호 등 구체적인 정보를 명확히 전달하세요
4. **제품 추천 시: 2-3개 소개 → 반드시 [PRODUCTS:ID1,ID2,ID3] 추가**
5. **매장 정보 시: 주소 안내 → 반드시 [STORE:D176] 추가**
6. **응답은 20-30초 이내로 매우 짧고 간결하게**
   - 핵심 정보만 2-3문장
   - 긴 설명 금지
7. [PRODUCTS:...] [STORE:...] 태그는 음성으로 읽히지 않으므로 걱정하지 마세요

[중요]
- 실제로 존재하지 않는 매장이나 제품 정보를 만들어내지 마세요
- 위에 명시된 정보만 사용하세요
- 가격 정보는 참고용으로만 제공 (실시간 변경 가능)
- 의료적 조언이나 진단은 하지 마세요"""
        
        return prompt
    
    async def run(self, room_url: str, token: str = None, language: str = "ko"):
        """
        봇을 실행합니다.
        
        Args:
            room_url: Daily.co 룸 URL
            token: 인증 토큰 (선택사항)
            language: STT 언어 설정 (ko/en, 기본값: ko)
        """
        logger.info(f"Starting Olive Young Voice Assistant Bot (Language: {language})")
        
        # Daily transport 설정
        transport = DailyTransport(
            room_url,
            token,
            "올리브영 쇼핑 어시스턴트",
            DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                transcription_enabled=False,  # OpenAI Whisper만 사용 (Daily transcription 끔)
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2))
            ),
        )
        
        # STT 서비스 - OpenAI Whisper (한국어 인식 최고!)
        stt = OpenAISTTService(
            api_key=self.openai_api_key,
            model="whisper-1",
            language=language  # ko/en - Whisper는 한국어 인식이 매우 정확
        )
        
        # TTS 서비스 (텍스트 → 음성) - Cartesia
        # 한국어 여성 음성 옵션:
        # - 248be419-c632-4f23-adf1-5324ed7dbf1d (Jiwon - 젊고 활기찬, 명확함) ✓
        # - a8a1eb38-5f15-4c1d-8722-7ac0f329727d (Soyeon - 부드럽고 자연스러운)
        # 영어 여성 음성 옵션:
        # - 21b81c14-f85b-436d-aff5-43f2e788ecf8 (Sarah - 명확하고 활기찬) ✓
        # - 02070f63-4fd3-4b03-a8cf-ac1e4a1e5c4c (Natasha - 자연스럽고 친근한)
        voice_id = "248be419-c632-4f23-adf1-5324ed7dbf1d" if language == "ko" else "21b81c14-f85b-436d-aff5-43f2e788ecf8"
        tts = CartesiaTTSService(
            api_key=self.cartesia_api_key,
            voice_id=voice_id,  # 명확하고 활기찬 여성 음성
        )
        
        # LLM 서비스 (대화 처리) - OpenAI
        llm = OpenAILLMService(
            api_key=self.openai_api_key,
            model="gpt-4o-mini"
        )
        
        # 메시지 초기화 (few-shot 예제 포함)
        messages = [
            {
                "role": "system",
                "content": self.system_prompt
            },
            # Few-shot 예제 1: 제품 추천
            {
                "role": "user",
                "content": "인기 제품 추천해줘"
            },
            {
                "role": "assistant",
                "content": "토리든 다이브인 히알루론산 세럼과 달바 퍼스트 스프레이 세럼 추천드립니다. [PRODUCTS:A000000189261,A000000232724]"
            },
            # Few-shot 예제 2: 매장 정보
            {
                "role": "user",
                "content": "매장 어디 있어?"
            },
            {
                "role": "assistant",
                "content": "서울 중구 명동길 53에 있습니다. 명동역 8번 출구로 나오시면 됩니다. [STORE:D176]"
            },
            # Few-shot 예제 3: 제품 추천 (다른 예시)
            {
                "role": "user",
                "content": "스킨케어 제품 추천"
            },
            {
                "role": "assistant",
                "content": "에스트라 아토베리어 크림, 라로슈포제 시카플라스트, 웰라쥬 히알루로닉 앰플 추천드립니다. [PRODUCTS:A000000236338,A000000236101,A000000235247]"
            }
        ]
        
        # 사용자/어시스턴트 응답 집계기
        user_response_aggregator = LLMUserResponseAggregator(messages)
        assistant_response_aggregator = LLMAssistantResponseAggregator(messages)
        
        # 의도 판단 필터 (판단 LLM으로 AI 어시스턴트 호출 의도 판단)
        intent_filter = IntentDetectionFilter(self.openai_api_key)
        
        # 대화 내용 로거 (전역 WebSocket 매니저 사용) - Intent:YES만 기록
        transcript_logger = TranscriptLogger()
        
        # 파이프라인 구성 (OpenAI Whisper STT 사용)
        pipeline = Pipeline(
            [
                transport.input(),           # 오디오 입력
                stt,                         # OpenAI Whisper (한국어/영어 자동 감지)
                intent_filter,               # 의도 판단 LLM (필터링) - NO는 여기서 차단
                transcript_logger,           # 로깅 (Intent:YES만 기록)
                user_response_aggregator,    # 사용자 메시지 집계
                llm,                         # 응답 LLM (실제 답변)
                tts,                         # 텍스트 → 음성
                transport.output(),          # 오디오 출력
                assistant_response_aggregator  # 어시스턴트 응답 집계
            ]
        )
        
        # 파이프라인 태스크 생성
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=False,  # TTS 완료까지 중단 방지
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
        )
        
        # 첫 참가자 입장 이벤트 핸들러
        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            logger.info(f"✅ First participant joined: {participant['id']}")
            # OpenAI Whisper 사용하므로 Daily transcription 불필요
            # 초기 인사말
            logger.info("Sending initial greeting")
            messages.append({
                "role": "system",
                "content": "안녕하세요! 올리브영 쇼핑 어시스턴트입니다. 매장 정보나 제품 추천이 필요하시면 말씀해 주세요."
            })
        
        # 참가자 퇴장 이벤트 핸들러
        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            logger.info(f"❌ Participant left: {participant}")
            await task.queue_frame(EndFrame())
        
        # 봇 실행
        runner = PipelineRunner()
        await runner.run(task)


async def main():
    """메인 실행 함수 (테스트용)"""
    room_url = os.getenv("DAILY_ROOM_URL")
    if not room_url:
        logger.error("DAILY_ROOM_URL이 설정되지 않았습니다.")
        return
    
    bot = OliveYoungVoiceBot()
    await bot.run(room_url)


if __name__ == "__main__":
    asyncio.run(main())
