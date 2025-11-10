# 올리브영 HTML 파서 - AI 쇼핑 어시스턴트 데이터 생성기

## 🎯 목적

`oy_sample.html` 파일을 파싱하여 AI 쇼핑 어시스턴트가 참조할 수 있는 구조화된 JSON 데이터를 생성합니다.

## 📦 추출되는 데이터

### ✅ 사용자 요구사항 충족

| 항목 | 필드명 | 상태 |
|------|--------|------|
| 상품명 | `name` (tit) | ✅ |
| 제품사진 | `image_url` | ✅ |
| 가격 | `sale_price` (coast) | ✅ |
| 할인율 | `discount_rate` (per) | ✅ |
| 재고 | `stock_info` (btnStoreStockMainGoodsDetail) | ✅ |
| 매장사진 | `store_images` | ✅ |
| 층별안내 | `floor_map` | ⚠️ 동적 로드 |

**층별안내 참고:** HTML 스냅샷에서는 JavaScript로 동적 로드되는 지도 이미지를 추출할 수 없습니다. 실제 이미지가 필요한 경우 Selenium/Playwright 사용이 필요합니다.

## 🚀 사용법

### 1. 데이터 생성 (HTML 파싱)

```bash
python3 parse_oliveyoung_full.py oy_sample.html data/assistant_data.json
```

**결과:**
```
================================================================================
🛍️  올리브영 AI 쇼핑 어시스턴트 데이터 생성
================================================================================

📂 HTML 파일 로드 중: oy_sample.html
✅ 파일 크기: 502,998 bytes

🏢 매장 정보 추출 중...
   ✅ 매장명: 올리브영 명동 타운
   ✅ 주소: 서울특별시 중구 명동길 53 1~2층
   ✅ 전화: 02-736-5290
   ✅ 서비스: 스마트 반품, 택스리펀드, 간편 결제

🛒 상품 정보 추출 중...
✅ 14개 상품 발견
   ✅ 총 14개 상품 추출 완료

📦 카테고리별 분류 중...
   ✅ 스킨케어: 12개
   ✅ 클렌징: 1개
   ✅ 기타: 1개

📍 주변 매장 정보 추출 중...
   ✅ 49개 주변 매장 정보 추출

✅ 추출 완료!
```

### 2. 데이터 조회

```bash
# 전체 정보
python3 query_assistant_data.py data/assistant_data.json

# 매장 정보만
python3 query_assistant_data.py data/assistant_data.json --store

# 상품 검색
python3 query_assistant_data.py data/assistant_data.json --search 크림

# 특정 카테고리
python3 query_assistant_data.py data/assistant_data.json --category 스킨케어

# 주변 매장
python3 query_assistant_data.py data/assistant_data.json --nearby

# 가격대별 분석
python3 query_assistant_data.py data/assistant_data.json --price-range

# AI 응답 예제
python3 query_assistant_data.py data/assistant_data.json --examples
```

### 3. 웹 브라우저에서 보기

```bash
# 간단한 HTTP 서버 실행
python3 -m http.server 8000

# 브라우저에서 열기
open http://localhost:8000/view_assistant_data.html
```

## 📊 생성되는 JSON 구조

```json
{
  "metadata": {
    "extracted_at": "2025-11-10T17:24:14.446860",
    "extraction_method": "html_parsing",
    "source_file": "oy_sample.html",
    "version": "1.0"
  },
  "store": {
    "store_name": "올리브영 명동 타운",
    "store_id": "D176",
    "address": "서울특별시 중구 명동길 53 1~2층",
    "subway_info": "4호선 명동역 8번 출구 / 2호선 을지로입구역 5번 출구",
    "phone": "02-736-5290",
    "business_hours": { "월": "10:00 ~ 22:30", ... },
    "services": ["스마트 반품", "택스리펀드", "간편 결제"],
    "gift_services": ["기프트카드"],
    "store_images": ["https://image.oliveyoung.co.kr/..."],
    "description": "올리브영 명동 타운은..."
  },
  "products": {
    "total": 14,
    "by_category": {
      "스킨케어": [
        {
          "product_id": "A000000236338",
          "name": "[11월 올영픽] 에스트라 아토베리어365 크림...",
          "image_url": "https://image.oliveyoung.co.kr/...",
          "original_price": 59400,
          "discount_rate": 25,
          "sale_price": 44500,
          "stock_info": "재고 9개 이상",
          "stock_status": "재고있음"
        }
      ]
    },
    "all_products": [...]
  },
  "floor_map": {
    "available": false,
    "map_element_id": "townDabeoMap"
  },
  "nearby_stores": [
    {
      "name": "명동점",
      "store_id": "DDEC",
      "address": "서울특별시 중구 명동8길 14",
      "status": "영업 중",
      "hours": "월 10:00~22:30",
      "image": "https://...",
      "services": ["스마트 반품"]
    }
  ]
}
```

## 🤖 AI 어시스턴트 통합 예제

### Python에서 사용

```python
import json

# 데이터 로드
with open('data/assistant_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 매장 정보
store = data['store']
print(f"매장: {store['store_name']}")
print(f"주소: {store['address']}")
print(f"전화: {store['phone']}")

# 상품 검색
keyword = "크림"
matching_products = [
    p for p in data['products']['all_products']
    if keyword in p['name'] and p['stock_status'] == '재고있음'
]

# 결과 출력
for product in matching_products:
    print(f"""
상품: {product['name']}
가격: {product['sale_price']:,}원 ({product['discount_rate']}% 할인)
재고: {product['stock_info']}
    """)
```

### AI 프롬프트 예제

```python
def generate_prompt(user_query, data):
    store = data['store']
    products = data['products']['all_products']
    
    # 키워드 추출 및 관련 상품 필터링
    relevant_products = filter_products(user_query, products)
    
    prompt = f"""
당신은 {store['store_name']}의 친절한 쇼핑 어시스턴트입니다.

[매장 정보]
- 위치: {store['address']}
- 영업시간: {store['business_hours']['월']}
- 전화: {store['phone']}
- 지하철: {store['subway_info']}

[현재 재고 있는 관련 상품]
{format_products(relevant_products)}

[고객 질문]
{user_query}

위 정보를 바탕으로 고객에게 친절하고 유용한 답변을 제공해주세요.
상품을 추천할 때는 가격, 할인율, 재고 정보를 포함해주세요.
"""
    return prompt
```

## 📈 추출 통계 (oy_sample.html 기준)

| 항목 | 수량 |
|------|------|
| 총 상품 수 | 14개 |
| 카테고리 | 3개 (스킨케어 12, 클렌징 1, 기타 1) |
| 재고 있는 상품 | 14개 (100%) |
| 평균 할인율 | 32.2% |
| 평균 가격 | 29,543원 |
| 주변 매장 | 49개 |

## 📝 파일 구조

```
pipecat/
├── oy_sample.html                      # 원본 HTML 파일
├── parse_oliveyoung_full.py            # ⭐ HTML 파싱 스크립트
├── query_assistant_data.py             # ⭐ 데이터 조회 도구
├── view_assistant_data.html            # ⭐ 웹 뷰어
├── AI_ASSISTANT_DATA_GUIDE.md          # 상세 가이드
├── OLIVEYOUNG_PARSER_README.md         # 이 파일
└── data/
    └── assistant_data.json             # ⭐ 생성된 JSON 데이터
```

## 🔧 필요한 패키지

```bash
pip install beautifulsoup4
```

또는

```bash
pip install -r requirements.txt
```

## 💡 활용 사례

### 1. 상품 검색
"수분크림 추천해주세요" → 관련 상품 필터링 및 추천

### 2. 재고 확인
"세럼 재고 있나요?" → 재고 있는 세럼 제품 목록

### 3. 가격 문의
"2만원대 제품 뭐가 있나요?" → 가격대별 상품 필터링

### 4. 할인 정보
"할인하는 상품 뭐가 있어요?" → 할인율 높은 순 정렬

### 5. 매장 안내
"매장 어디 있어요?" → 주소, 영업시간, 지하철 안내

## ⚠️ 제한사항

1. **층별안내 이미지**
   - HTML 스냅샷에서는 추출 불가
   - 동적 로드되는 지도 이미지는 브라우저 자동화 필요

2. **실시간 재고**
   - HTML 스냅샷 기준이므로 실시간 재고와 차이 있을 수 있음
   - 실제 서비스에서는 API 연동 권장

3. **가격 정보**
   - 온라인몰 기준 가격
   - 매장 혜택에 따라 최종 가격 상이할 수 있음

## 🔄 업데이트 방법

새로운 HTML로 데이터 업데이트:

```bash
# 1. 새 HTML 파일 준비
# (브라우저에서 저장 또는 크롤러 사용)

# 2. 파싱 실행
python3 parse_oliveyoung_full.py new_page.html data/assistant_data.json

# 3. 확인
python3 query_assistant_data.py data/assistant_data.json --store
```

## 📚 추가 문서

- [AI_ASSISTANT_DATA_GUIDE.md](AI_ASSISTANT_DATA_GUIDE.md) - 상세 데이터 가이드
- [MANUAL_SCRAPING_GUIDE.md](MANUAL_SCRAPING_GUIDE.md) - 수동 스크래핑 가이드
- [USE_SAMPLE_DATA.md](USE_SAMPLE_DATA.md) - 샘플 데이터 사용법

## 🎉 완료!

이제 AI 쇼핑 어시스턴트에서 이 데이터를 참조하여 다음과 같은 질문에 답변할 수 있습니다:

✅ "올리브영 명동 타운 영업시간이 어떻게 되나요?"
✅ "수분크림 추천해주세요"
✅ "세럼 재고 있나요?"
✅ "2만원대 제품 뭐가 있나요?"
✅ "할인하는 상품 뭐가 있어요?"
✅ "매장 전화번호 알려주세요"
✅ "주변에 다른 매장도 있나요?"

---

**Created:** 2025-11-10
**Version:** 1.0

