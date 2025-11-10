# 올리브영 크롤러 사용 가이드

올리브영 웹사이트에서 매장 정보와 상품 데이터를 수집하는 크롤러입니다.

## 설치

### 1. 필요한 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. Playwright 브라우저 설치

Playwright를 처음 사용하는 경우 브라우저를 설치해야 합니다:

```bash
playwright install chromium
```

## 사용법

### 기본 사용

```python
import asyncio
from src.oliveyoung_crawler import OliveYoungCrawler

async def main():
    crawler = OliveYoungCrawler()
    
    # 브라우저 초기화 (headless=False면 브라우저가 보입니다)
    await crawler.init_browser(headless=False)
    
    try:
        # 명동 타운 매장의 상품 정보 수집
        products = await crawler.get_store_products(
            store_name="명동 타운",
            categories=['스킨케어', '메이크업', '마스크/팩']
        )
        
        print(f"총 {len(products['categories'])}개 카테고리의 상품을 수집했습니다.")
        
    finally:
        await crawler.close_browser()

if __name__ == "__main__":
    asyncio.run(main())
```

### 여러 매장 크롤링

```python
import asyncio
from src.oliveyoung_crawler import OliveYoungCrawler

async def main():
    crawler = OliveYoungCrawler()
    
    # 여러 매장 일괄 크롤링
    await crawler.crawl_all(
        store_names=["명동 타운", "강남역점", "홍대입구점"]
    )

if __name__ == "__main__":
    asyncio.run(main())
```

### 편리한 실행 스크립트

프로젝트에 포함된 `crawl.py` 스크립트를 사용하면 더 편리합니다:

```bash
# 명동 타운 매장 크롤링
python crawl.py --store "명동 타운"

# 특정 카테고리만 크롤링
python crawl.py --store "명동 타운" --categories "스킨케어,메이크업"

# 여러 매장 크롤링
python crawl.py --stores "명동 타운,강남역점,홍대입구점"

# 브라우저 숨김 모드
python crawl.py --store "명동 타운" --headless
```

## 출력 결과

크롤링된 데이터는 `data/` 디렉토리에 JSON 형식으로 저장됩니다:

```
data/
  └── products_명동_타운_20251110.json
```

### 데이터 구조

```json
{
  "store_name": "명동 타운",
  "crawled_at": "2025-11-10T10:30:00",
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
    ],
    "메이크업": [
      {
        "product_id": "A000456",
        "name": "롬앤 립틴트",
        "brand": "롬앤",
        "price": 8900,
        "image_url": "https://image.oliveyoung.co.kr/...",
        "stock_status": "품절"
      }
    ]
  }
}
```

## 주의사항

### 1. 웹사이트 구조 변경

올리브영 웹사이트의 HTML 구조가 변경되면 크롤러가 작동하지 않을 수 있습니다. 
이 경우 `oliveyoung_crawler.py`의 CSS 셀렉터를 수정해야 합니다.

### 2. 크롤링 정책

- 과도한 요청은 IP 차단의 원인이 될 수 있습니다
- 요청 사이에 적절한 지연 시간을 두세요 (기본 1-3초)
- robots.txt를 확인하고 준수하세요

### 3. 로그인이 필요한 경우

일부 정보는 로그인 후에만 접근 가능할 수 있습니다. 
이 경우 크롤러에 로그인 기능을 추가해야 합니다.

## 문제 해결

### 매장을 찾을 수 없을 때

실제 올리브영 웹사이트의 매장명과 정확히 일치하는지 확인하세요:
- "명동 타운" ✅
- "명동타운" ❌
- "명동점" ❌

### CSS 셀렉터 찾기

올리브영 웹사이트에서 F12를 눌러 개발자 도구를 열고:
1. Elements 탭에서 원하는 요소 우클릭
2. Copy > Copy selector 선택
3. 크롤러 코드의 해당 셀렉터 수정

### 동적 콘텐츠가 로드되지 않을 때

`wait_until` 옵션과 대기 시간을 조정하세요:

```python
await self.page.goto(url, wait_until="networkidle")
await asyncio.sleep(3)  # 대기 시간 증가
```

## 데이터 활용

크롤링한 데이터를 AI 챗봇에 연동하려면:

```python
from src.store_service import StoreService
import json

# 크롤링된 상품 데이터 로드
with open('data/products_명동_타운_20251110.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

# 기존 store_data.json에 상품 정보 추가
store_service = StoreService()
# ... 데이터 통합 로직
```

## 법적 고지

웹 크롤링은 다음 사항을 준수해야 합니다:
- 웹사이트의 이용약관 확인
- robots.txt 준수
- 개인정보 보호법 준수
- 저작권법 준수

상업적 이용 시 올리브영의 공식 API 사용을 권장합니다.

