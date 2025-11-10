# 올리브영 샘플 상품 데이터 사용 가이드

## 📌 왜 샘플 데이터를 사용하나요?

올리브영 웹사이트는 다음과 같은 이유로 실시간 크롤링이 어렵습니다:

1. **복잡한 JavaScript 프레임워크** - React/Vue 등 고급 프레임워크 사용
2. **동적 콘텐츠 로딩** - 사용자 인터랙션에 따라 콘텐츠 로드
3. **크롤링 방지 메커니즘** - 봇 감지 및 차단 시스템
4. **법적 문제** - 웹사이트 이용약관 위반 가능성

### ✅ 권장 방법

**개발 단계**: 샘플 데이터로 시스템 구축 (현재)
**운영 단계**: 올리브영 공식 API 사용 또는 수동 데이터 입력

## 📦 샘플 데이터 정보

### 파일 위치
```
data/sample_products.json
```

### 데이터 구조
```json
{
  "store_name": "올리브영 명동 타운",
  "store_id": "D101",
  "crawled_at": "2025-11-10T15:00:00",
  "categories": {
    "스킨케어": [...],
    "메이크업": [...],
    "마스크팩": [...],
    "클렌징": [...],
    "선케어": [...]
  },
  "total_products": 24,
  "categories_count": 5
}
```

### 포함된 상품 (총 24개)

#### 스킨케어 (5개)
- 토리든 다이브인 저분자 히알루론산 세럼 (25,000원)
- 라운드랩 1025 독도 토너 (18,900원)
- 코스알엑스 어드밴스드 스네일 96 뮤신 파워 에센스 (21,000원)
- 아이소이 불가리안 로즈 토너 (32,000원)
- 닥터자르트 시카페어 크림 (38,000원) - 품절

#### 메이크업 (5개)
- 롬앤 쥬시 래스팅 틴트 (8,900원)
- 클리오 킬커버 파운웨어 쿠션 (25,000원)
- 에뛰드 픽싱 틴트 (7,900원)
- 페리페라 잉크 더 벨벳 (9,500원)
- 더샘 커버 퍼펙션 팁 컨실러 (6,500원)

#### 마스크팩 (5개)
- 메디힐 N.M.F 아쿠아링 앰플 마스크 (1,500원)
- 티르티르 마스크 핏 레드 쿠션 (2,000원)
- 토리든 다이브인 마스크 (1,800원)
- CNP 프로폴리스 앰플 마스크 (2,500원)
- 아누아 어성초 77% 수딩 마스크 (1,600원) - 품절

#### 클렌징 (4개)
- 바닐라코 클린잇제로 클렌징밤 (18,900원)
- 코스알엑스 로우 pH 굿모닝 젤 클렌저 (12,000원)
- 센카 퍼펙트 휩 클렌징 폼 (8,900원)
- 이니스프리 그린티 클렌징 폼 (7,000원)

#### 선케어 (3개)
- 라운드랩 자작나무 수분 선크림 (15,900원)
- 이니스프리 톤업 노세범 선크림 (12,000원)
- 어뮤즈 딜라이트 크리스탈 선스틱 (14,000원) - 품절

## 🔧 데이터 활용 방법

### 1. Python에서 로드하기

```python
import json

# 샘플 데이터 로드
with open('data/sample_products.json', 'r', encoding='utf-8') as f:
    products_data = json.load(f)

# 매장 정보
print(f"매장: {products_data['store_name']}")
print(f"총 상품: {products_data['total_products']}개")

# 카테고리별 상품
for category, products in products_data['categories'].items():
    print(f"\n{category} ({len(products)}개):")
    for product in products:
        print(f"  - {product['name']}: {product['price']:,}원 ({product['stock_status']})")
```

### 2. 재고 있는 상품만 필터링

```python
# 재고 있는 상품만
available_products = []
for category, products in products_data['categories'].items():
    for product in products:
        if product['stock_status'] == '재고있음':
            product['category'] = category
            available_products.append(product)

print(f"재고 있는 상품: {len(available_products)}개")
```

### 3. 가격대별 검색

```python
# 10,000원 이하 상품
affordable_products = []
for category, products in products_data['categories'].items():
    for product in products:
        if product['price'] <= 10000:
            print(f"{product['name']}: {product['price']:,}원")
```

### 4. AI 챗봇과 연동

```python
from src.store_service import StoreService

# 기존 매장 서비스
store_service = StoreService()

# 샘플 상품 데이터 로드
with open('data/sample_products.json', 'r', encoding='utf-8') as f:
    products_data = json.load(f)

# 챗봇에서 상품 추천 예시
def recommend_products(category, max_price=None):
    """카테고리와 가격으로 상품 추천"""
    if category not in products_data['categories']:
        return f"{category} 카테고리가 없습니다."
    
    products = products_data['categories'][category]
    
    # 재고 있고 가격 조건 만족하는 상품
    result = []
    for product in products:
        if product['stock_status'] == '재고있음':
            if max_price is None or product['price'] <= max_price:
                result.append(product)
    
    return result

# 사용 예시
skincare = recommend_products('스킨케어', max_price=20000)
for product in skincare:
    print(f"{product['name']}: {product['price']:,}원")
```

## 🤖 AI 쇼핑 어시스턴트 통합

### bot.py에 상품 검색 함수 추가

```python
def get_product_info(category=None, product_name=None, max_price=None):
    """상품 정보 조회"""
    with open('data/sample_products.json', 'r', encoding='utf-8') as f:
        products_data = json.load(f)
    
    # 카테고리 필터
    if category:
        if category in products_data['categories']:
            products = products_data['categories'][category]
        else:
            return f"{category} 카테고리가 없습니다."
    else:
        # 전체 상품
        products = []
        for cat_products in products_data['categories'].values():
            products.extend(cat_products)
    
    # 상품명 검색
    if product_name:
        products = [p for p in products if product_name.lower() in p['name'].lower()]
    
    # 가격 필터
    if max_price:
        products = [p for p in products if p['price'] <= max_price]
    
    # 재고 있는 상품만
    products = [p for p in products if p['stock_status'] == '재고있음']
    
    return products
```

### 대화 예시

**사용자**: "스킨케어 제품 추천해줘"
**AI**: "명동 타운점에 재고가 있는 스킨케어 제품입니다:
- 라운드랩 1025 독도 토너 (18,900원)
- 코스알엑스 어드밴스드 스네일 96 뮤신 파워 에센스 (21,000원)
- 토리든 다이브인 저분자 히알루론산 세럼 (25,000원)
- 아이소이 불가리안 로즈 토너 (32,000원)"

**사용자**: "2만원 이하로 있어?"
**AI**: "네, 2만원 이하 스킨케어 제품은:
- 라운드랩 1025 독도 토너 (18,900원)"

**사용자**: "립틴트 뭐 있어?"
**AI**: "명동 타운점에 재고가 있는 틴트 제품입니다:
- 롬앤 쥬시 래스팅 틴트 (8,900원)
- 에뛰드 픽싱 틴트 (7,900원)
- 페리페라 잉크 더 벨벳 (9,500원)"

## 📝 데이터 업데이트 방법

### 수동으로 상품 추가

`data/sample_products.json` 파일을 직접 편집:

```json
{
  "product_id": "A006234567",
  "name": "새로운 상품명",
  "brand": "브랜드명",
  "price": 15000,
  "image_url": "https://image.oliveyoung.co.kr/...",
  "stock_status": "재고있음",
  "description": "상품 설명"
}
```

### 실제 매장 방문 후 데이터 입력

1. 올리브영 매장 방문
2. 재고 확인
3. `sample_products.json` 업데이트
4. AI 챗봇에 반영

## 🚀 운영 단계 전환

### 실제 서비스 준비

1. **올리브영 공식 API 문의**
   - 올리브영 B2B 담당 부서에 API 사용 문의
   - 파트너십 체결

2. **데이터베이스 구축**
   - JSON → PostgreSQL/MySQL 이관
   - 실시간 재고 업데이트 시스템

3. **관리자 페이지 구축**
   - 상품 정보 수동 입력 인터페이스
   - 재고 관리 시스템

## 💡 장점

✅ **법적 문제 없음** - 크롤링 대신 수동 데이터 관리
✅ **안정적 운영** - 웹사이트 변경에 영향 없음
✅ **빠른 응답** - 로컬 데이터로 즉시 응답
✅ **테스트 용이** - 개발/테스트 환경 구축 간편

## 📞 실제 크롤링이 꼭 필요한 경우

1. **셀레니움 + 수동 조작** 방식
2. **올리브영 모바일 앱 API 리버스 엔지니어링** (비권장)
3. **올리브영 공식 파트너십** (권장)

---

**결론**: 샘플 데이터로 시스템을 완성하고, 운영 단계에서는 공식 API나 수동 관리 방식을 사용하는 것을 권장합니다.

