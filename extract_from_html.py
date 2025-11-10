#!/usr/bin/env python3
"""
올리브영 HTML 파일에서 상품 데이터 추출

사용법:
  python3 extract_from_html.py oy_sample.html data/extracted_products.json
"""

import sys
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime


def extract_products_from_html(html_file):
    """HTML 파일에서 상품 정보 추출"""
    
    print(f"📂 HTML 파일 로드 중: {html_file}")
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    print(f"✅ 파일 크기: {len(html_content):,} bytes")
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 다양한 상품 리스트 선택자 시도
    selectors = [
        '#stockGoodsList li',
        '#goodsList li',
        '.list_store_prdt li',
        'li[class*="prd"]',
        'ul li a[onclick*="storeInfos"]'
    ]
    
    all_products = []
    found_selector = None
    
    for selector in selectors:
        elements = soup.select(selector)
        if elements:
            print(f"✅ '{selector}' 선택자로 {len(elements)}개 요소 발견")
            found_selector = selector
            
            # 상품 정보 추출
            for idx, elem in enumerate(elements, 1):
                try:
                    product = extract_product_info(elem, idx)
                    if product and product.get('name'):
                        all_products.append(product)
                except Exception as e:
                    print(f"  ⚠️  상품 {idx} 추출 오류: {e}")
                    continue
            
            if all_products:
                break
    
    if not all_products:
        print("❌ 상품 데이터를 찾을 수 없습니다.")
        print("\n💡 HTML 구조 분석:")
        
        # HTML 구조 분석
        analyze_html_structure(soup)
    
    return all_products, found_selector


def extract_product_info(elem, idx):
    """개별 상품 요소에서 정보 추출"""
    
    # 링크 요소 찾기
    link = elem.find('a')
    if not link:
        link = elem
    
    # onclick 속성에서 정보 추출
    onclick = link.get('onclick', '')
    product_id = ''
    product_name = ''
    
    if onclick:
        # onclick="storeInfos.storeStockMain.getProductStockDetail('A000123', '상품명', ...)"
        matches = re.findall(r"'([^']+)'", onclick)
        if len(matches) >= 2:
            product_id = matches[0]
            product_name = matches[1]
    
    # 상품명이 없으면 텍스트에서 추출
    if not product_name:
        # 다양한 클래스명 시도
        name_elem = elem.select_one('.prd-name, .prod_name, .product-name, .name, .tit, h3, .title')
        if name_elem:
            product_name = name_elem.get_text(strip=True)
    
    # 이미지
    img = elem.find('img')
    image_url = ''
    if img:
        image_url = img.get('src') or img.get('data-src') or ''
        if image_url and not image_url.startswith('http'):
            if image_url.startswith('//'):
                image_url = 'https:' + image_url
            elif image_url.startswith('/'):
                image_url = 'https://www.oliveyoung.co.kr' + image_url
    
    # 텍스트에서 가격과 재고 추출
    text = elem.get_text(strip=True)
    
    # 가격 추출
    price = 0
    price_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*원', text)
    if price_match:
        price = int(price_match.group(1).replace(',', ''))
    
    # 재고 상태
    stock_status = '확인 필요'
    if '재고있음' in text or '재고 있음' in text:
        stock_status = '재고있음'
    elif '품절' in text or '재고없음' in text or '재고 없음' in text:
        stock_status = '품절'
    
    # 브랜드
    brand = ''
    brand_elem = elem.select_one('.brand, .prd-brand, .brand-name')
    if brand_elem:
        brand = brand_elem.get_text(strip=True)
    
    # 상품명이 있으면 반환
    if product_name:
        return {
            'product_id': product_id,
            'name': product_name,
            'brand': brand,
            'price': price,
            'image_url': image_url,
            'stock_status': stock_status
        }
    
    return None


def analyze_html_structure(soup):
    """HTML 구조 분석"""
    
    # 주요 ID들
    print("\n주요 ID 요소:")
    for id_val in ['stockGoodsList', 'goodsList', 'storeStockMain', 'storeList']:
        elem = soup.find(id=id_val)
        if elem:
            print(f"  ✅ #{id_val} 발견")
            # 하위 li 개수
            lis = elem.find_all('li', recursive=True)
            print(f"     → 하위 li 요소: {len(lis)}개")
    
    # 클래스명 검색
    print("\n주요 클래스 요소:")
    for class_name in ['list_store_prdt', 'prd_item', 'product-item']:
        elems = soup.find_all(class_=class_name)
        if elems:
            print(f"  ✅ .{class_name} : {len(elems)}개")
    
    # onclick 속성 가진 링크
    links_with_onclick = soup.find_all('a', onclick=True)
    print(f"\nonclick 속성 가진 링크: {len(links_with_onclick)}개")
    
    if links_with_onclick:
        print("  처음 3개 onclick 예시:")
        for link in links_with_onclick[:3]:
            onclick = link.get('onclick', '')[:100]
            print(f"    - {onclick}...")


def categorize_products(products):
    """상품을 카테고리별로 분류 (추측)"""
    
    categories = {
        '스킨케어': [],
        '메이크업': [],
        '마스크/팩': [],
        '클렌징': [],
        '선케어': [],
        '기타': []
    }
    
    # 키워드로 카테고리 추측
    skincare_keywords = ['세럼', '토너', '에센스', '크림', '로션', '앰플']
    makeup_keywords = ['틴트', '립', '쿠션', '파운데이션', '컨실러', '아이', '섀도우', '마스카라', '치크']
    mask_keywords = ['마스크', '팩', '시트']
    cleansing_keywords = ['클렌징', '세안', '폼', '워시', '젤', '밤']
    suncare_keywords = ['선크림', '선케어', '자외선', 'SPF', '썬']
    
    for product in products:
        name = product['name'].lower()
        
        categorized = False
        
        if any(kw in name for kw in mask_keywords):
            categories['마스크/팩'].append(product)
            categorized = True
        elif any(kw in name for kw in makeup_keywords):
            categories['메이크업'].append(product)
            categorized = True
        elif any(kw in name for kw in cleansing_keywords):
            categories['클렌징'].append(product)
            categorized = True
        elif any(kw in name for kw in suncare_keywords):
            categories['선케어'].append(product)
            categorized = True
        elif any(kw in name for kw in skincare_keywords):
            categories['스킨케어'].append(product)
            categorized = True
        
        if not categorized:
            categories['기타'].append(product)
    
    # 빈 카테고리 제거
    return {k: v for k, v in categories.items() if v}


def main():
    if len(sys.argv) < 2:
        print("""
올리브영 HTML 파싱 도구

사용법:
  python3 extract_from_html.py <html_file> [output_file]

예시:
  python3 extract_from_html.py oy_sample.html data/extracted_products.json
        """)
        return
    
    html_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'data/extracted_products.json'
    
    if not Path(html_file).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {html_file}")
        return
    
    print("="*70)
    print("🔍 올리브영 HTML 파싱 시작")
    print("="*70 + "\n")
    
    # 상품 추출
    products, selector = extract_products_from_html(html_file)
    
    if not products:
        print("\n❌ 상품을 추출하지 못했습니다.")
        return
    
    print(f"\n✅ 총 {len(products)}개 상품 추출 완료!")
    
    # 카테고리별 분류
    print("\n📦 카테고리별 분류 중...")
    categorized = categorize_products(products)
    
    # 결과 데이터 구성
    result = {
        'store_name': '올리브영 명동 타운',
        'store_id': 'D101',
        'crawled_at': datetime.now().isoformat(),
        'extraction_method': 'html_parsing',
        'selector_used': selector,
        'categories': categorized,
        'total_products': len(products),
        'categories_count': len(categorized)
    }
    
    # 저장
    output_path = Path(output_file)
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 결과 출력
    print("\n" + "="*70)
    print("✅ 추출 완료!")
    print("="*70)
    print(f"총 상품: {len(products)}개")
    print(f"카테고리: {len(categorized)}개\n")
    
    for category, items in categorized.items():
        print(f"📦 {category}: {len(items)}개")
        for i, product in enumerate(items[:3], 1):
            print(f"   {i}. {product['name'][:50]}... - {product['price']:,}원 ({product['stock_status']})")
        if len(items) > 3:
            print(f"   ... 외 {len(items) - 3}개")
        print()
    
    print(f"📁 저장 위치: {output_file}")
    
    # 통계
    stock_available = sum(1 for p in products if p['stock_status'] == '재고있음')
    stock_out = sum(1 for p in products if p['stock_status'] == '품절')
    
    print(f"\n📊 재고 현황:")
    print(f"  재고있음: {stock_available}개")
    print(f"  품절: {stock_out}개")
    print(f"  확인 필요: {len(products) - stock_available - stock_out}개")


if __name__ == "__main__":
    main()

