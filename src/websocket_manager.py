"""
WebSocket 연결 관리 모듈
"""
from loguru import logger
import json

# 전역 WebSocket 저장소
_active_websockets = {}


def add_websocket(client_id, websocket):
    """WebSocket 연결 추가"""
    _active_websockets[client_id] = websocket
    logger.info(f"✅ WebSocket added: {client_id}, Total: {len(_active_websockets)}")


def remove_websocket(client_id):
    """WebSocket 연결 제거"""
    if client_id in _active_websockets:
        del _active_websockets[client_id]
        logger.info(f"🗑️ WebSocket removed: {client_id}, Remaining: {len(_active_websockets)}")


def get_active_websockets():
    """활성 WebSocket 딕셔너리 반환"""
    return _active_websockets


async def broadcast_message(data: dict):
    """모든 WebSocket에 메시지 전송"""
    message = json.dumps(data)
    disconnected = []
    
    logger.info(f"📤 Broadcasting to {len(_active_websockets)} WebSocket(s): {data}")
    
    for client_id, ws in list(_active_websockets.items()):
        try:
            await ws.send_text(message)
            logger.info(f"✅ Sent to WebSocket {client_id}")
        except Exception as e:
            logger.error(f"❌ Error sending to WebSocket {client_id}: {e}")
            disconnected.append(client_id)
    
    # 연결 끊긴 소켓 제거
    for client_id in disconnected:
        remove_websocket(client_id)

