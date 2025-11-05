#!/bin/bash

# 올리브영 음성 쇼핑 어시스턴트 실행 스크립트

echo "🛍️ 올리브영 음성 쇼핑 어시스턴트 시작..."

# .env 파일 확인
if [ ! -f .env ]; then
    echo "❌ .env 파일이 없습니다."
    echo "📝 .env.example을 복사하여 .env 파일을 생성하고 API 키를 입력하세요."
    echo ""
    echo "cp .env.example .env"
    exit 1
fi

# UV가 설치되어 있는지 확인
if ! command -v uv &> /dev/null; then
    echo "❌ UV가 설치되어 있지 않습니다."
    echo "📥 다음 명령어로 설치하세요:"
    echo ""
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# 의존성 설치 (필요한 경우)
echo "📦 의존성 확인 중..."
uv sync

# 서버 실행
echo "🚀 서버 시작 중..."
echo "🌐 브라우저에서 http://localhost:8000 에 접속하세요"
echo ""

uv run python -m src.server

