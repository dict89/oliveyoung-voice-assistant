"""
올리브영 음성 쇼핑 어시스턴트 봇
Pipecat을 사용한 실시간 음성 대화 구현 (WebRTC Transport)
"""
import asyncio
import os
import sys

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMMessagesFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.services.cartesia import CartesiaSTTService, CartesiaTTSService
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams, FastAPIWebsocketTransport

from loguru import logger
from dotenv import load_dotenv

from .store_service import StoreService

# 환경 변수 로드
load_dotenv()

# 로거 설정
logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


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
        
        # 매장 정보 요약
        stores_summary = "\n".join([
            f"- {store['name']} ({store['store_id']}): {store['address']}"
            for store in self.store_service.get_all_stores()
        ])
        
        # 카테고리 정보
        categories = self.store_service.get_categories()
        categories_summary = ", ".join(categories.keys())
        
        prompt = f"""당신은 올리브영(Olive Young)의 친절한 AI 쇼핑 어시스턴트입니다.

[역할]
- 고객에게 올리브영 매장 정보를 안내합니다
- 제품 추천과 쇼핑 관련 질문에 답변합니다
- 항상 친절하고 전문적인 톤으로 응대합니다
- 자연스러운 대화체를 사용합니다

[제공 가능한 정보]
1. 매장 위치, 영업시간, 연락처
2. 매장별 특징 및 제공 서비스
3. 교통 정보 및 주변 랜드마크
4. 인기 제품 및 추천
5. 제품 카테고리: {categories_summary}

[현재 등록된 매장]
{stores_summary}

[응대 가이드라인]
1. 고객의 질문을 정확히 이해하고 관련 정보를 제공하세요
2. 매장 위치를 물으면 주소와 함께 가까운 지하철역이나 랜드마크를 안내하세요
3. 영업시간, 전화번호 등 구체적인 정보를 명확히 전달하세요
4. 제품 추천 시에는 현재 인기 있는 제품을 소개하세요
5. 정보가 없는 경우 솔직히 말하고 다른 방법을 제안하세요
6. 응답은 간결하면서도 충분한 정보를 담도록 하세요 (음성 대화임을 고려)
7. 특수 문자는 사용하지 마세요 (음성으로 변환되므로)

[중요]
- 실제로 존재하지 않는 매장이나 제품 정보를 만들어내지 마세요
- 위에 명시된 매장 정보만 사용하세요
- 가격 정보는 제공하지 않습니다 (실시간으로 변경될 수 있음)
- 의료적 조언이나 진단은 하지 마세요"""
        
        return prompt
    
    def create_transport_params(self) -> FastAPIWebsocketParams:
        """WebSocket Transport 파라미터를 생성합니다."""
        return FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
        )
    
    async def run_bot(self, transport: BaseTransport):
        """
        봇을 실행합니다.
        
        Args:
            transport: Pipecat transport 인스턴스
        """
        logger.info("Starting Olive Young Voice Assistant Bot")
        
        # STT 서비스 (음성 → 텍스트) - Cartesia
        stt = CartesiaSTTService(
            api_key=self.cartesia_api_key,
            language="ko"  # 한국어 설정
        )
        
        # TTS 서비스 (텍스트 → 음성) - Cartesia
        tts = CartesiaTTSService(
            api_key=self.cartesia_api_key,
            voice_id="a167e0f3-df7e-4d52-a9c3-f949145efdab",  # 한국어 음성 (필요시 변경)
        )
        
        # LLM 서비스 (대화 처리) - OpenAI
        llm = OpenAILLMService(
            api_key=self.openai_api_key,
            model="gpt-4o-mini"  # 또는 "gpt-4o"
        )
        
        # 대화 컨텍스트 초기화
        messages = [
            {
                "role": "system",
                "content": self.system_prompt
            }
        ]
        
        context = LLMContext(messages)
        context_aggregator = LLMContextAggregatorPair(context)
        
        # 파이프라인 구성
        pipeline = Pipeline(
            [
                transport.input(),           # 오디오 입력
                stt,                         # 음성 → 텍스트
                context_aggregator.user(),   # 사용자 메시지 집계
                llm,                         # LLM 처리
                tts,                         # 텍스트 → 음성
                transport.output(),          # 오디오 출력
                context_aggregator.assistant()  # 어시스턴트 응답 집계
            ]
        )
        
        # 파이프라인 태스크 생성
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
        )
        
        # 클라이언트 연결 이벤트 핸들러
        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            logger.info("Client connected")
            # 초기 인사말
            initial_message = {
                "role": "system",
                "content": "안녕하세요! 올리브영 쇼핑 어시스턴트입니다. 매장 정보나 제품 추천이 필요하시면 말씀해 주세요."
            }
            messages.append(initial_message)
            await task.queue_frames([LLMMessagesFrame(messages)])
        
        # 클라이언트 연결 해제 이벤트 핸들러
        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            logger.info("Client disconnected")
            await task.cancel()
        
        # 봇 실행
        runner = PipelineRunner()
        await runner.run(task)


async def main():
    """메인 실행 함수 (테스트용)"""
    from fastapi import FastAPI, WebSocket
    import uvicorn
    
    app = FastAPI()
    bot = OliveYoungVoiceBot()
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        
        transport_params = bot.create_transport_params()
        transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=transport_params
        )
        
        await bot.run_bot(transport)
    
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
