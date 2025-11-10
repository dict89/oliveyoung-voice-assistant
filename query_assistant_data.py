#!/usr/bin/env python3
"""
AI 쇼핑 어시스턴트용 데이터 조회 도구

사용법:
  python3 query_assistant_data.py data/assistant_data.json
"""

import sys
import json
from pathlib import Path


def format_price(price):
    """가격 포맷팅"""
    return f"{price:,}원"


def display_store_info(data):
    """매장 정보 표시"""
    store = data['store']
    
    print("\n" + "="*80)
    print("🏢 매장 정보")
    print("="*80)
    print(f"매장명: {store['store_name']}")
    print(f"Store ID: {store['store_id']}")
    print(f"주소: {store['address']}")
    print(f"지하철: {store['subway_info']}")
    print(f"전화: {store['phone']}")
    
    if store['store_images']:
        print(f"\n📸 매장 사진:")
        for img in store['store_images']:
            print(f"  - {img}")
    
    print(f"\n⏰ 영업시간:")
    for day, hours in store['business_hours'].items():
        print(f"  {day}: {hours}")
    
    print(f"\n🎁 서비스:")
    for service in store['services']:
        print(f"  ✓ {service}")
    
    if store['gift_services']:
        print(f"\n🎫 상품권:")
        for gift in store['gift_services']:
            print(f"  ✓ {gift}")
    
    print(f"\n📝 매장 소개:")
    print(f"  {store['description']}")


def display_products_summary(data):
    """상품 요약 정보 표시"""
    products = data['products']
    
    print("\n" + "="*80)
    print("🛍️  상품 정보")
    print("="*80)
    print(f"총 상품: {products['total']}개")
    
    print(f"\n📦 카테고리별 상품 수:")
    for category, items in products['by_category'].items():
        print(f"  {category}: {len(items)}개")


def display_category_products(data, category=None):
    """카테고리별 상품 상세 표시"""
    products = data['products']['by_category']
    
    if category and category in products:
        categories = {category: products[category]}
    else:
        categories = products
    
    for cat_name, items in categories.items():
        print(f"\n" + "="*80)
        print(f"📦 {cat_name} ({len(items)}개)")
        print("="*80)
        
        for idx, product in enumerate(items, 1):
            print(f"\n{idx}. {product['name']}")
            print(f"   상품번호: {product['product_id']}")
            print(f"   가격: {format_price(product['sale_price'])} (정가: {format_price(product['original_price'])})")
            if product['discount_rate'] > 0:
                print(f"   할인: {product['discount_rate']}% 할인")
            print(f"   재고: {product['stock_info']} ({product['stock_status']})")
            print(f"   이미지: {product['image_url']}")


def search_products(data, keyword):
    """상품 검색"""
    all_products = data['products']['all_products']
    
    results = [p for p in all_products if keyword.lower() in p['name'].lower()]
    
    print(f"\n🔍 '{keyword}' 검색 결과: {len(results)}개")
    print("="*80)
    
    if not results:
        print("검색 결과가 없습니다.")
        return
    
    for idx, product in enumerate(results, 1):
        print(f"\n{idx}. {product['name']}")
        print(f"   상품번호: {product['product_id']}")
        print(f"   가격: {format_price(product['sale_price'])}")
        if product['discount_rate'] > 0:
            print(f"   할인: {product['discount_rate']}% 할인 (정가: {format_price(product['original_price'])})")
        print(f"   재고: {product['stock_info']}")


def display_nearby_stores(data, limit=10):
    """주변 매장 표시"""
    stores = data['nearby_stores']
    
    print("\n" + "="*80)
    print(f"📍 주변 매장 ({len(stores)}개)")
    print("="*80)
    
    for idx, store in enumerate(stores[:limit], 1):
        print(f"\n{idx}. {store['name']}")
        print(f"   주소: {store['address']}")
        print(f"   영업: {store.get('status', 'N/A')} - {store.get('hours', 'N/A')}")
        if store.get('services'):
            print(f"   서비스: {', '.join(store['services'])}")


def display_price_range(data):
    """가격대별 상품 분석"""
    all_products = data['products']['all_products']
    
    if not all_products:
        return
    
    print("\n" + "="*80)
    print("💰 가격대별 분석")
    print("="*80)
    
    # 가격대 구간
    ranges = [
        (0, 10000, "1만원 이하"),
        (10000, 20000, "1만원대"),
        (20000, 30000, "2만원대"),
        (30000, 40000, "3만원대"),
        (40000, 50000, "4만원대"),
        (50000, float('inf'), "5만원 이상")
    ]
    
    for min_price, max_price, label in ranges:
        products_in_range = [p for p in all_products 
                            if min_price <= p['sale_price'] < max_price]
        if products_in_range:
            print(f"\n{label}: {len(products_in_range)}개")
            avg_discount = sum(p['discount_rate'] for p in products_in_range) / len(products_in_range)
            print(f"  평균 할인율: {avg_discount:.1f}%")
            
            # 상위 3개 표시
            for product in products_in_range[:3]:
                print(f"  - {product['name'][:50]}... ({format_price(product['sale_price'])})")


def generate_assistant_response_examples(data):
    """AI 어시스턴트 응답 예제 생성"""
    print("\n" + "="*80)
    print("🤖 AI 쇼핑 어시스턴트 응답 예제")
    print("="*80)
    
    store = data['store']
    products = data['products']
    
    # 예제 1: 매장 안내
    print("\n📌 예제 1: '올리브영 명동 타운 영업시간이 어떻게 되나요?'")
    print("-" * 80)
    print(f"{store['store_name']}의 영업시간은 다음과 같습니다:")
    print(f"월~일요일, 휴일 모두 {store['business_hours']['월']} 영업합니다.")
    print(f"위치: {store['address']}")
    print(f"지하철: {store['subway_info']}")
    
    # 예제 2: 상품 추천
    print("\n📌 예제 2: '수분크림 추천해주세요'")
    print("-" * 80)
    all_products = products['all_products']
    cream_products = [p for p in all_products if '크림' in p['name'] and '수분' in p['name']]
    
    if cream_products:
        top_product = cream_products[0]
        print(f"추천 상품: {top_product['name']}")
        print(f"가격: {format_price(top_product['sale_price'])} ({top_product['discount_rate']}% 할인)")
        print(f"재고: {top_product['stock_info']}")
    
    # 예제 3: 재고 확인
    print("\n📌 예제 3: '세럼 재고 있나요?'")
    print("-" * 80)
    serum_products = [p for p in all_products if '세럼' in p['name'] and p['stock_status'] == '재고있음']
    print(f"현재 세럼 제품 {len(serum_products)}개가 재고 있습니다:")
    for product in serum_products[:3]:
        print(f"- {product['name'][:60]}...")
        print(f"  {format_price(product['sale_price'])} ({product['stock_info']})")
    
    # 예제 4: 할인 상품
    print("\n📌 예제 4: '할인하는 상품 뭐가 있나요?'")
    print("-" * 80)
    discount_products = sorted([p for p in all_products if p['discount_rate'] > 0], 
                               key=lambda x: x['discount_rate'], reverse=True)
    print(f"현재 {len(discount_products)}개 상품이 할인 중입니다. 최대 할인 상품:")
    for product in discount_products[:3]:
        print(f"- {product['name'][:60]}...")
        print(f"  {product['discount_rate']}% 할인 → {format_price(product['sale_price'])}")


def main():
    if len(sys.argv) < 2:
        print("""
AI 쇼핑 어시스턴트 데이터 조회 도구

사용법:
  python3 query_assistant_data.py <json_file> [옵션]

옵션:
  --store          매장 정보만 표시
  --products       상품 요약 표시
  --category <이름> 특정 카테고리 상품 표시
  --search <키워드> 상품 검색
  --nearby         주변 매장 표시
  --price-range    가격대별 분석
  --examples       AI 응답 예제 표시
  --all            모든 정보 표시 (기본값)

예시:
  python3 query_assistant_data.py data/assistant_data.json --store
  python3 query_assistant_data.py data/assistant_data.json --search 크림
  python3 query_assistant_data.py data/assistant_data.json --category 스킨케어
        """)
        return
    
    json_file = sys.argv[1]
    
    if not Path(json_file).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {json_file}")
        return
    
    print(f"📂 데이터 로드 중: {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 옵션 처리
    if len(sys.argv) == 2 or '--all' in sys.argv:
        display_store_info(data)
        display_products_summary(data)
        display_nearby_stores(data, limit=5)
        display_price_range(data)
        generate_assistant_response_examples(data)
    else:
        if '--store' in sys.argv:
            display_store_info(data)
        
        if '--products' in sys.argv:
            display_products_summary(data)
        
        if '--category' in sys.argv:
            idx = sys.argv.index('--category')
            if idx + 1 < len(sys.argv):
                category = sys.argv[idx + 1]
                display_category_products(data, category)
        
        if '--search' in sys.argv:
            idx = sys.argv.index('--search')
            if idx + 1 < len(sys.argv):
                keyword = sys.argv[idx + 1]
                search_products(data, keyword)
        
        if '--nearby' in sys.argv:
            display_nearby_stores(data)
        
        if '--price-range' in sys.argv:
            display_price_range(data)
        
        if '--examples' in sys.argv:
            generate_assistant_response_examples(data)


if __name__ == "__main__":
    main()

