# AI 쇼핑 어시스턴트 데이터 가이드

## 📋 개요

`oy_sample.html` 파일을 파싱하여 AI 쇼핑 어시스턴트가 참조할 수 있는 구조화된 데이터를 생성합니다.

## 🚀 빠른 시작

### 1. HTML 파싱하여 데이터 생성

```bash
python3 parse_oliveyoung_full.py oy_sample.html data/assistant_data.json
```

### 2. 생성된 데이터 조회

```bash
# 전체 정보 보기
python3 query_assistant_data.py data/assistant_data.json

# 매장 정보만 보기
python3 query_assistant_data.py data/assistant_data.json --store

# 상품 검색
python3 query_assistant_data.py data/assistant_data.json --search 크림

# 특정 카테고리 보기
python3 query_assistant_data.py data/assistant_data.json --category 스킨케어

# AI 응답 예제 보기
python3 query_assistant_data.py data/assistant_data.json --examples
```

## 📊 추출되는 데이터

### 1. 매장 정보 (Store Information)

```json
{
  "store": {
    "store_name": "올리브영 명동 타운",
    "store_id": "D176",
    "address": "서울특별시 중구 명동길 53 1~2층",
    "subway_info": "4호선 명동역 8번 출구 / 2호선 을지로입구역 5번 출구",
    "phone": "02-736-5290",
    "business_hours": {
      "월": "10:00 ~ 22:30",
      "화": "10:00 ~ 22:30",
      ...
    },
    "services": ["스마트 반품", "택스리펀드", "간편 결제"],
    "gift_services": ["기프트카드"],
    "store_images": ["https://image.oliveyoung.co.kr/..."],
    "description": "올리브영 명동 타운은 최신 K-뷰티를..."
  }
}
```

**추출 필드:**
- ✅ 매장명 (store_name)
- ✅ 매장 ID (store_id)
- ✅ 주소 (address)
- ✅ 지하철 정보 (subway_info)
- ✅ 전화번호 (phone)
- ✅ 영업시간 (business_hours)
- ✅ 매장 서비스 (services)
- ✅ 상품권 판매 (gift_services)
- ✅ 매장 사진 (store_images) 📸
- ✅ 매장 설명 (description)

### 2. 상품 정보 (Products)

```json
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
```

**추출 필드:**
- ✅ 상품번호 (product_id)
- ✅ 상품명 (name / tit) 📝
- ✅ 제품사진 (image_url) 📸
- ✅ 정가 (original_price)
- ✅ 최종가격 (sale_price / coast) 💰
- ✅ 할인율 (discount_rate / per) 🏷️
- ✅ 재고정보 (stock_info / btnStoreStockMainGoodsDetail) 📦
- ✅ 재고상태 (stock_status)

### 3. 카테고리별 분류

자동으로 다음 카테고리로 분류됩니다:

- 📦 **스킨케어** - 세럼, 토너, 에센스, 크림, 로션, 앰플, 미스트
- 💄 **메이크업** - 틴트, 립, 쿠션, 파운데이션, 아이섀도우
- 🎭 **마스크/팩** - 마스크, 팩, 시트
- 🧴 **클렌징** - 클렌징, 세안, 폼, 워시, 젤
- ☀️ **선케어** - 선크림, 자외선차단제
- 💇 **헤어케어** - 샴푸, 린스, 트리트먼트
- 🧼 **바디케어** - 바디로션, 핸드크림
- 🌸 **향수** - 향수, 퍼퓸, 디퓨저
- 💊 **건강식품** - 비타민, 영양제, 콜라겐

### 4. 주변 매장 정보

```json
{
  "name": "명동점",
  "store_id": "DDEC",
  "address": "서울특별시 중구 명동8길 14",
  "status": "영업 중",
  "hours": "월 10:00~22:30",
  "image": "https://image.oliveyoung.co.kr/...",
  "services": ["스마트 반품"]
}
```

### 5. 층별안내 (Floor Map) 🗺️

```json
{
  "floor_map": {
    "available": true/false,
    "note": "층별안내 기능이 있으나, 동적으로 로드되는 지도 이미지는 HTML에서 추출 불가"
  }
}
```

**참고:** 층별안내 지도는 JavaScript로 동적 로드되므로 정적 HTML에서는 이미지 URL을 추출할 수 없습니다. 
실제 구현 시에는 브라우저 자동화(Selenium/Playwright) 필요합니다.

## 🤖 AI 어시스턴트 활용 예제

### 예제 1: 매장 정보 안내

**사용자 질문:** "올리브영 명동 타운 영업시간이 어떻게 되나요?"

**AI 응답 (데이터 참조):**
```python
store = data['store']
response = f"""
{store['store_name']}의 영업시간은 다음과 같습니다:
- 평일/주말/휴일 모두: {store['business_hours']['월']}

📍 위치: {store['address']}
🚇 지하철: {store['subway_info']}
📞 전화: {store['phone']}

매장 서비스:
{', '.join(store['services'])}
"""
```

### 예제 2: 상품 검색 및 추천

**사용자 질문:** "수분크림 추천해주세요"

**AI 응답 (데이터 참조):**
```python
# 크림 상품 필터링
products = data['products']['all_products']
cream_products = [p for p in products 
                  if '크림' in p['name'] and '수분' in p['name'] 
                  and p['stock_status'] == '재고있음']

# 할인율 높은 순 정렬
cream_products.sort(key=lambda x: x['discount_rate'], reverse=True)

top_product = cream_products[0]
response = f"""
추천 상품: {top_product['name']}

💰 가격: {top_product['sale_price']:,}원
🏷️ 할인: {top_product['discount_rate']}% (정가 {top_product['original_price']:,}원)
📦 재고: {top_product['stock_info']}
📸 상품 이미지: {top_product['image_url']}
"""
```

### 예제 3: 재고 확인

**사용자 질문:** "세럼 재고 있나요?"

**AI 응답 (데이터 참조):**
```python
serum_products = [p for p in data['products']['all_products']
                  if '세럼' in p['name'] and p['stock_status'] == '재고있음']

response = f"현재 세럼 제품 {len(serum_products)}개가 재고 있습니다:\n\n"
for product in serum_products[:5]:
    response += f"✓ {product['name']}\n"
    response += f"  {product['sale_price']:,}원 ({product['stock_info']})\n\n"
```

### 예제 4: 가격대별 상품 안내

**사용자 질문:** "2만원대 제품 뭐가 있나요?"

**AI 응답 (데이터 참조):**
```python
products_20k = [p for p in data['products']['all_products']
                if 20000 <= p['sale_price'] < 30000]

response = f"2만원대 제품 {len(products_20k)}개가 있습니다:\n\n"
for product in products_20k:
    response += f"• {product['name']}\n"
    response += f"  {product['sale_price']:,}원 ({product['discount_rate']}% 할인)\n"
```

### 예제 5: 할인 상품 안내

**사용자 질문:** "지금 할인하는 상품 뭐가 있어요?"

**AI 응답 (데이터 참조):**
```python
# 할인율 높은 순
discount_products = sorted([p for p in data['products']['all_products']],
                          key=lambda x: x['discount_rate'], reverse=True)

response = f"현재 {len(discount_products)}개 상품이 할인 중입니다!\n\n"
response += "🔥 최대 할인 상품 TOP 5:\n\n"
for i, product in enumerate(discount_products[:5], 1):
    response += f"{i}. {product['name']}\n"
    response += f"   {product['discount_rate']}% 할인 → {product['sale_price']:,}원\n"
    response += f"   (정가: {product['original_price']:,}원)\n\n"
```

## 📁 파일 구조

```
pipecat/
├── oy_sample.html                    # 원본 HTML 파일
├── parse_oliveyoung_full.py          # HTML 파싱 스크립트
├── query_assistant_data.py           # 데이터 조회 도구
├── AI_ASSISTANT_DATA_GUIDE.md        # 이 파일
└── data/
    └── assistant_data.json           # 생성된 JSON 데이터
```

## 🔧 기술 스택

- **Python 3.x**
- **BeautifulSoup4** - HTML 파싱
- **JSON** - 데이터 저장 형식

## 📈 추출 통계 (oy_sample.html 기준)

- ✅ 매장 정보: 1개
- ✅ 상품 정보: 14개
- ✅ 카테고리: 3개 (스킨케어 12개, 클렌징 1개, 기타 1개)
- ✅ 주변 매장: 49개
- ✅ 재고 있는 상품: 14개 (100%)
- ✅ 평균 할인율: 32.2%
- ✅ 평균 가격: 29,543원

## 💡 AI 어시스턴트 통합 팁

### 1. 데이터 로드

```python
import json

# 데이터 로드
with open('data/assistant_data.json', 'r', encoding='utf-8') as f:
    store_data = json.load(f)

store = store_data['store']
products = store_data['products']['all_products']
categories = store_data['products']['by_category']
nearby = store_data['nearby_stores']
```

### 2. 벡터 검색을 위한 텍스트 생성

```python
# 상품별 검색용 텍스트 생성
for product in products:
    search_text = f"""
    상품명: {product['name']}
    가격: {product['sale_price']}원
    할인율: {product['discount_rate']}%
    재고: {product['stock_info']}
    """
    # 이 텍스트를 임베딩하여 벡터 DB에 저장
```

### 3. 컨텍스트 구성

```python
def get_context_for_query(user_query, data):
    """사용자 질문에 맞는 컨텍스트 구성"""
    
    context = {
        'store_info': data['store'],
        'relevant_products': [],
        'nearby_stores': []
    }
    
    # 키워드 기반 상품 필터링
    keywords = extract_keywords(user_query)
    for product in data['products']['all_products']:
        if any(kw in product['name'].lower() for kw in keywords):
            context['relevant_products'].append(product)
    
    return context
```

### 4. 프롬프트 예제

```python
prompt = f"""
당신은 올리브영 매장의 친절한 쇼핑 어시스턴트입니다.

매장 정보:
- 매장명: {store['store_name']}
- 위치: {store['address']}
- 영업시간: {store['business_hours']['월']}

현재 재고 있는 관련 상품:
{format_products(relevant_products)}

고객 질문: {user_query}

위 정보를 바탕으로 친절하게 답변해주세요.
"""
```

## 🚨 주의사항

### 1. 층별안내 이미지

- HTML에서 층별안내 지도 이미지는 **추출 불가** (동적 로드)
- 실제 이미지가 필요한 경우 Selenium/Playwright 사용 필요

### 2. 실시간 재고

- HTML 스냅샷 기준이므로 실시간 재고와 차이 있을 수 있음
- 실제 서비스에서는 API 연동 권장

### 3. 가격 정보

- 온라인몰 기준 가격
- 매장 혜택에 따라 최종 가격 상이할 수 있음

## 🔄 업데이트 방법

새로운 HTML 파일로 데이터 업데이트:

```bash
# 1. 새 HTML 다운로드
# (브라우저에서 페이지 저장 또는 크롤러 사용)

# 2. 파싱 실행
python3 parse_oliveyoung_full.py new_store_page.html data/assistant_data.json

# 3. 데이터 확인
python3 query_assistant_data.py data/assistant_data.json --store
```

## 📞 문의 및 지원

데이터 구조나 활용 방법에 대한 문의는 프로젝트 이슈로 등록해주세요.

---

**Last Updated:** 2025-11-10
**Version:** 1.0

