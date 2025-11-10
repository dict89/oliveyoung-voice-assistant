# 크롬 개발자 도구로 올리브영 데이터 수동 추출하기 🔍

자동 크롤링이 어려울 때 가장 확실한 방법은 **브라우저에서 직접 데이터를 추출**하는 것입니다!

## 📋 목차

1. [방법 1: Network 탭에서 API 응답 가져오기](#방법-1-network-탭에서-api-응답-가져오기)
2. [방법 2: Console에서 DOM 데이터 추출하기](#방법-2-console에서-dom-데이터-추출하기)
3. [방법 3: Elements 탭에서 HTML 복사하기](#방법-3-elements-탭에서-html-복사하기)

---

## 방법 1: Network 탭에서 API 응답 가져오기 ⭐ (추천)

이 방법이 가장 깔끔하고 구조화된 데이터를 얻을 수 있습니다.

### 단계 1: 개발자 도구 열기

1. 올리브영 매장 페이지 접속: https://www.oliveyoung.co.kr/store/store/getStoreInfoMain.do
2. **F12** 또는 **Cmd+Option+I** (Mac) 눌러 개발자 도구 열기
3. **Network** 탭 선택
4. 🔴 **빨간 Record 버튼**이 켜져 있는지 확인

### 단계 2: 매장 선택 및 재고 조회

1. "명동 타운" 매장 검색
2. 매장 클릭
3. **"재고 조회"** 버튼 클릭
4. **카테고리 버튼** (스킨케어, 메이크업 등) 클릭

### 단계 3: API 호출 찾기

Network 탭에서 다음을 찾으세요:

```
📁 Name 열에서 찾을 것:
  - getProductList
  - getStockList
  - search
  - goods
  - product
  
또는 XHR 필터 클릭하여 Ajax 요청만 보기
```

### 단계 4: API 응답 복사

1. API 호출 클릭 (예: `getProductList`)
2. **Response** 탭 선택
3. JSON 데이터가 보이면:
   - 우클릭 → **Copy** → **Copy response**
4. 또는 전체 선택 (Ctrl+A) → 복사 (Ctrl+C)

### 단계 5: JSON 파일로 저장

```bash
# 복사한 데이터를 파일로 저장
cat > data/oliveyoung_skincare_raw.json
# Ctrl+V로 붙여넣기
# Ctrl+D로 저장
```

또는 텍스트 에디터에 붙여넣고 저장:
```
data/oliveyoung_skincare_raw.json
data/oliveyoung_makeup_raw.json
```

---

## 방법 2: Console에서 DOM 데이터 추출하기 🎯

JavaScript로 페이지의 DOM 요소를 직접 추출합니다.

### 단계 1: Console 탭 열기

1. F12 → **Console** 탭
2. 매장 페이지에서 재고 조회 → 카테고리 선택 (데이터가 로드된 상태)

### 단계 2: JavaScript 코드 실행

Console에 다음 코드를 복사해서 실행:

```javascript
// 상품 목록 추출 함수
function extractProducts() {
    const products = [];
    
    // 상품 리스트 요소 찾기
    const productElements = document.querySelectorAll('#stockGoodsList li, #goodsList li, .list_store_prdt li');
    
    console.log(`발견된 상품 요소: ${productElements.length}개`);
    
    productElements.forEach((elem, index) => {
        try {
            // 링크 요소
            const link = elem.querySelector('a');
            if (!link) return;
            
            // onclick 속성에서 정보 추출
            const onclick = link.getAttribute('onclick') || '';
            
            // 상품명과 코드 추출 (예: 'A123456', '토리든 세럼', ...)
            const matches = onclick.match(/'([^']+)'/g);
            let productId = '';
            let productName = '';
            
            if (matches && matches.length >= 2) {
                productId = matches[0].replace(/'/g, '');
                productName = matches[1].replace(/'/g, '');
            }
            
            // 이미지
            const img = elem.querySelector('img');
            const imageUrl = img ? (img.src || img.dataset.src || '') : '';
            
            // 텍스트에서 가격 추출
            const text = elem.innerText;
            const priceMatch = text.match(/(\d{1,3}(?:,\d{3})*)\s*원/);
            const price = priceMatch ? parseInt(priceMatch[1].replace(/,/g, '')) : 0;
            
            // 재고 상태
            let stockStatus = '확인 필요';
            if (text.includes('재고있음') || text.includes('재고 있음')) {
                stockStatus = '재고있음';
            } else if (text.includes('품절') || text.includes('재고없음')) {
                stockStatus = '품절';
            }
            
            // 브랜드 추출 (있으면)
            const brandElem = elem.querySelector('.brand, .prd-brand');
            const brand = brandElem ? brandElem.innerText.trim() : '';
            
            if (productName) {
                products.push({
                    product_id: productId,
                    name: productName,
                    brand: brand,
                    price: price,
                    image_url: imageUrl,
                    stock_status: stockStatus
                });
            }
        } catch (e) {
            console.error(`상품 ${index} 추출 오류:`, e);
        }
    });
    
    return products;
}

// 실행 및 결과 출력
const products = extractProducts();
console.log(`총 ${products.length}개 상품 추출 완료`);
console.log(JSON.stringify(products, null, 2));

// 클립보드에 복사
copy(products);
console.log('✅ 데이터가 클립보드에 복사되었습니다!');
```

### 단계 3: 결과 저장

1. Console에 JSON 데이터가 출력됨
2. `copy(products)` 명령으로 자동으로 클립보드에 복사됨
3. 텍스트 에디터에 붙여넣고 저장:
   ```bash
   # 붙여넣은 내용을 파일로 저장
   # data/oliveyoung_products_manual.json
   ```

### 🎨 카테고리별로 추출하기

```javascript
// 카테고리 정보 포함
function extractProductsWithCategory(categoryName) {
    const products = extractProducts();
    return {
        category: categoryName,
        crawled_at: new Date().toISOString(),
        products: products
    };
}

// 사용 예시
const skincare = extractProductsWithCategory('스킨케어');
copy(skincare);
console.log('스킨케어 데이터 복사 완료!');
```

---

## 방법 3: Elements 탭에서 HTML 복사하기

### 단계 1: Elements 탭에서 요소 선택

1. F12 → **Elements** 탭
2. 왼쪽 위 **요소 선택 도구** (화살표 아이콘) 클릭
3. 페이지에서 상품 요소 클릭

### 단계 2: HTML 복사

1. Elements 탭에서 상품 리스트 영역 찾기 (예: `<ul id="stockGoodsList">`)
2. 해당 요소 **우클릭**
3. **Copy** → **Copy outerHTML**

### 단계 3: HTML 파일로 저장

```bash
# HTML 저장
cat > data/oliveyoung_products.html
# Ctrl+V로 붙여넣기
# Ctrl+D로 저장
```

### 단계 4: Python으로 파싱

```python
from bs4 import BeautifulSoup
import json

# HTML 로드
with open('data/oliveyoung_products.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

products = []
for li in soup.select('li'):
    # 상품 정보 추출
    link = li.select_one('a')
    if link and link.get('onclick'):
        onclick = link.get('onclick')
        # onclick에서 상품 정보 추출
        # ...

# JSON으로 저장
with open('data/products.json', 'w', encoding='utf-8') as f:
    json.dump(products, f, ensure_ascii=False, indent=2)
```

---

## 🔄 전체 워크플로우

### 📦 모든 카테고리 데이터 수집하기

```javascript
// 1. Console에 이 함수들을 먼저 실행
function extractProducts() {
    // ... 위의 extractProducts 함수 전체 복사
}

// 2. 카테고리별로 데이터 수집
const categories = ['스킨케어', '메이크업', '마스크/팩', '클렌징', '선케어'];
const allData = {
    store_name: '올리브영 명동 타운',
    store_id: 'D101',
    crawled_at: new Date().toISOString(),
    categories: {}
};

// 3. 각 카테고리 버튼을 클릭할 때마다 실행
// (카테고리 버튼 클릭 → 3초 대기 → 아래 코드 실행)

function saveCurrentCategory(categoryName) {
    const products = extractProducts();
    allData.categories[categoryName] = products;
    console.log(`${categoryName}: ${products.length}개 저장됨`);
    copy(allData);
    console.log('✅ 전체 데이터 클립보드 복사 완료');
}

// 사용법:
// 1. "스킨케어" 버튼 클릭 → 데이터 로드 → saveCurrentCategory('스킨케어')
// 2. "메이크업" 버튼 클릭 → 데이터 로드 → saveCurrentCategory('메이크업')
// 3. 반복...
```

---

## 💾 데이터 구조 변환하기

### JSON 정리 스크립트

수동으로 추출한 데이터를 정리:

```python
import json

# 수동 추출 데이터 로드
with open('data/oliveyoung_products_manual.json', 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

# 정리
cleaned_data = {
    'store_name': '올리브영 명동 타운',
    'crawled_at': raw_data.get('crawled_at', '2025-11-10'),
    'categories': {}
}

# 카테고리별로 정리
for category, products in raw_data.get('categories', {}).items():
    cleaned_products = []
    for p in products:
        if p.get('name'):  # 이름이 있는 것만
            cleaned_products.append({
                'product_id': p.get('product_id', ''),
                'name': p['name'],
                'brand': p.get('brand', ''),
                'price': p.get('price', 0),
                'image_url': p.get('image_url', ''),
                'stock_status': p.get('stock_status', '확인 필요'),
                'description': p.get('description', '')
            })
    
    cleaned_data['categories'][category] = cleaned_products

# 저장
with open('data/products_cleaned.json', 'w', encoding='utf-8') as f:
    json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

print(f"✅ {len(cleaned_data['categories'])}개 카테고리, 총 {sum(len(p) for p in cleaned_data['categories'].values())}개 상품 저장")
```

---

## 🎯 실전 예제

### 완전 자동화된 추출 스크립트

Console에 한번에 복사해서 사용:

```javascript
// === 올리브영 상품 데이터 추출기 ===
(function() {
    console.log('🚀 올리브영 데이터 추출 시작...');
    
    // 상품 추출
    const products = [];
    const elements = document.querySelectorAll('#stockGoodsList li, #goodsList li, .list_store_prdt li');
    
    elements.forEach((elem, idx) => {
        try {
            const link = elem.querySelector('a');
            if (!link) return;
            
            const onclick = link.getAttribute('onclick') || '';
            const matches = onclick.match(/'([^']+)'/g);
            
            let id = '', name = '';
            if (matches && matches.length >= 2) {
                id = matches[0].replace(/'/g, '');
                name = matches[1].replace(/'/g, '');
            }
            
            const img = elem.querySelector('img');
            const imgUrl = img ? (img.src || img.dataset.src || '') : '';
            
            const text = elem.innerText;
            const priceMatch = text.match(/(\d{1,3}(?:,\d{3})*)\s*원/);
            const price = priceMatch ? parseInt(priceMatch[1].replace(/,/g, '')) : 0;
            
            let stock = '확인 필요';
            if (text.includes('재고있음')) stock = '재고있음';
            else if (text.includes('품절')) stock = '품절';
            
            const brandElem = elem.querySelector('.brand, .prd-brand');
            const brand = brandElem ? brandElem.innerText.trim() : '';
            
            if (name) {
                products.push({
                    product_id: id,
                    name: name,
                    brand: brand,
                    price: price,
                    image_url: imgUrl,
                    stock_status: stock
                });
            }
        } catch (e) {
            console.warn(`상품 ${idx} 추출 실패:`, e);
        }
    });
    
    // 결과
    const result = {
        extracted_at: new Date().toISOString(),
        category: '카테고리명을 여기에 입력',
        product_count: products.length,
        products: products
    };
    
    console.log(`✅ ${products.length}개 상품 추출 완료!`);
    console.table(products.slice(0, 5)); // 처음 5개만 테이블로 표시
    
    // 클립보드에 복사
    copy(result);
    console.log('📋 데이터가 클립보드에 복사되었습니다!');
    console.log('📝 텍스트 에디터에 붙여넣어 저장하세요.');
    
    return result;
})();
```

### 사용 방법:

1. 올리브영 재고 조회 페이지에서 카테고리 클릭
2. 데이터 로드 후 F12 → Console
3. 위 스크립트 전체 복사 → 붙여넣기 → Enter
4. 자동으로 클립보드에 복사됨
5. VSCode나 메모장에 붙여넣고 `data/category_name.json`으로 저장

---

## 📱 모바일에서도 가능!

### Chrome 모바일 개발자 도구

1. PC Chrome에서: chrome://inspect
2. USB로 휴대폰 연결
3. 휴대폰에서 올리브영 앱 or 모바일 웹 접속
4. PC에서 Inspect 클릭
5. 위와 동일한 방법으로 데이터 추출

---

## 🎉 최종 체크리스트

### 데이터 추출 완료 확인

- [ ] Network 탭에서 API 응답 확인
- [ ] Console에서 JavaScript로 DOM 추출
- [ ] 각 카테고리별로 데이터 수집
- [ ] JSON 파일로 저장
- [ ] 데이터 검증 (상품명, 가격, 재고 등)
- [ ] `data/` 폴더에 정리
- [ ] Python으로 로드 테스트

### 저장된 파일 예시

```
data/
├── oliveyoung_skincare.json
├── oliveyoung_makeup.json
├── oliveyoung_maskpack.json
├── oliveyoung_cleansing.json
└── oliveyoung_suncare.json
```

---

## 💡 팁

### 1. **여러 페이지 수집**
- 페이지네이션이 있으면 각 페이지마다 반복
- "더보기" 버튼이 있으면 클릭 후 스크롤

### 2. **이미지 다운로드**
```javascript
// 이미지 URL 목록 추출
const imageUrls = [...document.querySelectorAll('img')]
    .map(img => img.src)
    .filter(url => url.includes('oliveyoung'));
copy(imageUrls);
```

### 3. **자동 반복**
```javascript
// 모든 카테고리 버튼 찾기
const categoryButtons = document.querySelectorAll('button[onclick*="getGoodsList"]');
console.log(`${categoryButtons.length}개 카테고리 발견`);
```

---

## 🚨 주의사항

1. **저작권**: 수집한 데이터는 개인 프로젝트 용도로만 사용
2. **이용약관**: 올리브영 이용약관 확인
3. **상업적 이용**: 공식 API나 파트너십 필요
4. **데이터 갱신**: 가격/재고는 자주 변경되므로 주기적 업데이트 필요

---

**이 방법이 가장 확실하고 법적으로도 안전합니다!** 🎯

브라우저에서 보이는 것을 그대로 복사하는 것이므로 크롤링 방지 메커니즘을 우회할 필요가 없습니다.

