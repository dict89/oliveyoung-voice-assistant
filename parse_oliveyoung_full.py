#!/usr/bin/env python3
"""
올리브영 HTML 완전 파싱 - AI 쇼핑 어시스턴트용 데이터 생성

사용법:
  python3 parse_oliveyoung_full.py oy_sample.html data/assistant_data.json
"""

import sys
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime


def parse_store_info(soup):
    """매장 정보 추출"""
    store_info = {
        'store_name': '',
        'store_id': '',
        'address': '',
        'subway_info': '',
        'phone': '',
        'business_hours': {},
        'services': [],
        'gift_services': [],
        'store_images': [],
        'description': ''
    }
    
    # 매장명 - 더 정확한 선택자 사용
    store_name_elem = soup.select_one('.tit_zone .tit')
    if not store_name_elem:
        store_name_elem = soup.select_one('.store_info_detail .tit_zone .tit')
    if store_name_elem:
        store_info['store_name'] = store_name_elem.get_text(strip=True)
    
    # Store ID 추출 (링크에서)
    store_link = soup.select_one('a[href*="getStockStoreDetail"]')
    if store_link:
        href = store_link.get('href', '')
        # javascript:storeInfos.storeDetail.getStockStoreDetail('D176', '올리브영 명동 타운')
        match = re.search(r"getStockStoreDetail\('([^']+)'", href)
        if match:
            store_info['store_id'] = match.group(1)
    
    # 매장 설명
    desc_elem = soup.select_one('.shop_detail_txt dd')
    if desc_elem:
        store_info['description'] = desc_elem.get_text(strip=True)
    
    # 주소
    address_elem = soup.select_one('._address')
    if address_elem:
        store_info['address'] = address_elem.get_text(strip=True)
    
    # 지하철 정보
    subway_elem = soup.select_one('.addr .sub')
    if subway_elem:
        store_info['subway_info'] = subway_elem.get_text(strip=True)
    
    # 전화번호
    phone_elem = soup.select_one('._shopTel')
    if phone_elem:
        store_info['phone'] = phone_elem.get_text(strip=True)
    
    # 영업시간
    workday_list = soup.select('._workdayList li')
    for item in workday_list:
        day = item.select_one('strong')
        time = item.select_one('span')
        if day and time:
            day_text = day.get_text(strip=True)
            time_text = time.get_text(strip=True)
            store_info['business_hours'][day_text] = time_text
    
    # 매장 서비스
    service_list = soup.select('._storeServiceList li')
    store_info['services'] = [s.get_text(strip=True) for s in service_list]
    
    # 상품권 판매
    gift_list = soup.select('._giftServiceList li')
    store_info['gift_services'] = [g.get_text(strip=True) for g in gift_list]
    
    # 매장 이미지
    store_img_elem = soup.select_one('#storeDetailImage')
    if store_img_elem:
        style = store_img_elem.get('style', '')
        # background-image: url("...") 에서 URL 추출
        urls = re.findall(r'url\(["\']?(https?://[^)"\']+)["\']?\)', style)
        store_info['store_images'] = [url for url in urls if 'noimg' not in url]
    
    return store_info


def parse_products(soup):
    """상품 정보 추출"""
    products = []
    
    # stockGoodsList에서 상품 찾기
    product_items = soup.select('#stockGoodsList li')
    
    print(f"✅ {len(product_items)}개 상품 발견")
    
    for idx, item in enumerate(product_items, 1):
        try:
            product = {}
            
            # 상품 번호
            link = item.select_one('a[data-goodsno]')
            if link:
                product['product_id'] = link.get('data-goodsno', '')
            else:
                product['product_id'] = ''
            
            # 상품명
            tit_elem = item.select_one('.tit')
            if tit_elem:
                product['name'] = tit_elem.get_text(strip=True)
            else:
                product['name'] = ''
            
            # 상품 이미지
            img = item.select_one('.img_zone img')
            if img:
                product['image_url'] = img.get('src', '')
            else:
                product['image_url'] = ''
            
            # 가격 정보
            price_zone = item.select_one('.price')
            
            # 정가 (pre)
            pre_elem = price_zone.select_one('.pre') if price_zone else None
            if pre_elem:
                price_text = pre_elem.get_text(strip=True)
                price_text = re.sub(r'[^\d]', '', price_text)
                product['original_price'] = int(price_text) if price_text else 0
            else:
                product['original_price'] = 0
            
            # 할인율 (per)
            per_elem = price_zone.select_one('.per') if price_zone else None
            if per_elem:
                discount_text = per_elem.get_text(strip=True)
                discount_text = re.sub(r'[^\d]', '', discount_text)
                product['discount_rate'] = int(discount_text) if discount_text else 0
            else:
                product['discount_rate'] = 0
            
            # 최종가격 (coast)
            coast_elem = price_zone.select_one('.coast') if price_zone else None
            if coast_elem:
                # "25,650원~" 형태에서 숫자만 추출
                coast_text = coast_elem.get_text(strip=True)
                coast_text = re.sub(r'[^\d]', '', coast_text)
                product['sale_price'] = int(coast_text) if coast_text else 0
            else:
                product['sale_price'] = 0
            
            # 재고 정보 (btnStoreStockMainGoodsDetail)
            stock_btn = item.select_one('._btnStoreStockMainGoodsDetail .num')
            if stock_btn:
                stock_text = stock_btn.get_text(strip=True)
                product['stock_info'] = stock_text
                
                # 재고 상태 분류
                if '품절' in stock_text or '재고 없음' in stock_text:
                    product['stock_status'] = '품절'
                elif '재고' in stock_text:
                    if '9개 이상' in stock_text:
                        product['stock_status'] = '재고있음'
                    else:
                        # "재고 3개" 같은 형태
                        product['stock_status'] = '재고있음'
                else:
                    product['stock_status'] = '확인필요'
            else:
                product['stock_info'] = '정보 없음'
                product['stock_status'] = '확인필요'
            
            # 상품 정보가 유효한 경우만 추가
            if product.get('name'):
                products.append(product)
                
        except Exception as e:
            print(f"  ⚠️  상품 {idx} 추출 오류: {e}")
            continue
    
    return products


def categorize_products(products):
    """상품을 카테고리별로 분류"""
    
    categories = {
        '스킨케어': [],
        '메이크업': [],
        '마스크/팩': [],
        '클렌징': [],
        '선케어': [],
        '헤어케어': [],
        '바디케어': [],
        '향수': [],
        '건강식품': [],
        '기타': []
    }
    
    # 키워드 매핑
    keyword_map = {
        '스킨케어': ['세럼', '토너', '에센스', '크림', '로션', '앰플', '미스트', '수분', '보습'],
        '메이크업': ['틴트', '립', '쿠션', '파운데이션', '컨실러', '아이', '섀도우', '마스카라', '치크', '아이브로우'],
        '마스크/팩': ['마스크', '팩', '시트'],
        '클렌징': ['클렌징', '세안', '폼', '워시', '젤', '밤', '리무버'],
        '선케어': ['선크림', '선케어', '자외선', 'SPF', '썬'],
        '헤어케어': ['샴푸', '린스', '트리트먼트', '헤어', '두피'],
        '바디케어': ['바디', '핸드', '풋', '로션', '크림', '워시'],
        '향수': ['향수', '퍼퓸', '프래그런스', '디퓨저'],
        '건강식품': ['비타민', '영양제', '건강', '콜라겐', '프로바이오틱스']
    }
    
    for product in products:
        name = product['name'].lower()
        categorized = False
        
        for category, keywords in keyword_map.items():
            if any(kw in name for kw in keywords):
                categories[category].append(product)
                categorized = True
                break
        
        if not categorized:
            categories['기타'].append(product)
    
    # 빈 카테고리 제거
    return {k: v for k, v in categories.items() if v}


def parse_floor_map_info(soup):
    """층별안내 정보 추출"""
    floor_info = {
        'available': False,
        'floors': [],
        'map_element_id': 'townDabeoMap'
    }
    
    # 층별안내 버튼 리스트 확인
    floor_btns = soup.select('#btnFloorList li')
    if floor_btns:
        floor_info['available'] = True
        floor_info['note'] = '층별안내 기능이 있으나, 동적으로 로드되는 지도 이미지는 HTML에서 추출 불가'
    
    return floor_info


def extract_nearby_stores(soup):
    """주변 매장 목록 추출"""
    stores = []
    
    store_items = soup.select('#storeList li')
    
    for item in store_items:
        try:
            store = {}
            
            # 매장명
            name_elem = item.select_one('.txt_tit')
            if name_elem:
                store['name'] = name_elem.get_text(strip=True)
            
            # 주소
            addr_elem = item.select_one('.txt_addr')
            if addr_elem:
                store['address'] = addr_elem.get_text(strip=True)
            
            # 영업 상태
            status_elem = item.select_one('.txt_status .day')
            if status_elem:
                store['status'] = status_elem.get_text(strip=True)
            
            # 영업 시간
            time_elem = item.select_one('.txt_status .time')
            if time_elem:
                store['hours'] = time_elem.get_text(strip=True)
            
            # 매장 이미지
            img = item.select_one('.img_thubnail img')
            if img:
                store['image'] = img.get('src', '')
            
            # 태그 (서비스)
            tags = item.select('.tags_area .tag')
            store['services'] = [tag.get_text(strip=True) for tag in tags]
            
            # Store ID 추출 (링크에서)
            link = item.select_one('a[href*="getStockStoreDetail"]')
            if link:
                href = link.get('href', '')
                # javascript:storeInfos.storeDetail.getStockStoreDetail('D176', '올리브영 명동 타운')
                match = re.search(r"getStockStoreDetail\('([^']+)'", href)
                if match:
                    store['store_id'] = match.group(1)
            
            if store.get('name'):
                stores.append(store)
                
        except Exception as e:
            print(f"  ⚠️  매장 정보 추출 오류: {e}")
            continue
    
    return stores


def main():
    if len(sys.argv) < 2:
        print("""
올리브영 HTML 완전 파싱 - AI 쇼핑 어시스턴트용

사용법:
  python3 parse_oliveyoung_full.py <html_file> [output_file]

예시:
  python3 parse_oliveyoung_full.py oy_sample.html data/assistant_data.json
        """)
        return
    
    html_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'data/assistant_data.json'
    
    if not Path(html_file).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {html_file}")
        return
    
    print("="*80)
    print("🛍️  올리브영 AI 쇼핑 어시스턴트 데이터 생성")
    print("="*80 + "\n")
    
    # HTML 로드
    print(f"📂 HTML 파일 로드 중: {html_file}")
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    print(f"✅ 파일 크기: {len(html_content):,} bytes\n")
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. 매장 정보 추출
    print("🏢 매장 정보 추출 중...")
    store_info = parse_store_info(soup)
    print(f"   ✅ 매장명: {store_info['store_name']}")
    print(f"   ✅ 주소: {store_info['address']}")
    print(f"   ✅ 전화: {store_info['phone']}")
    print(f"   ✅ 서비스: {', '.join(store_info['services'])}")
    print()
    
    # 2. 상품 정보 추출
    print("🛒 상품 정보 추출 중...")
    products = parse_products(soup)
    print(f"   ✅ 총 {len(products)}개 상품 추출 완료\n")
    
    # 3. 카테고리 분류
    print("📦 카테고리별 분류 중...")
    categorized = categorize_products(products)
    for cat, items in categorized.items():
        print(f"   ✅ {cat}: {len(items)}개")
    print()
    
    # 4. 층별안내 정보
    print("🗺️  층별안내 정보 추출 중...")
    floor_info = parse_floor_map_info(soup)
    if floor_info['available']:
        print(f"   ✅ {floor_info.get('note', '층별안내 정보 있음')}")
    else:
        print(f"   ℹ️  층별안내 정보 없음")
    print()
    
    # 5. 주변 매장
    print("📍 주변 매장 정보 추출 중...")
    nearby_stores = extract_nearby_stores(soup)
    print(f"   ✅ {len(nearby_stores)}개 주변 매장 정보 추출\n")
    
    # 최종 데이터 구성
    result = {
        'metadata': {
            'extracted_at': datetime.now().isoformat(),
            'extraction_method': 'html_parsing',
            'source_file': html_file,
            'version': '1.0'
        },
        'store': store_info,
        'products': {
            'total': len(products),
            'by_category': categorized,
            'all_products': products
        },
        'floor_map': floor_info,
        'nearby_stores': nearby_stores
    }
    
    # 저장
    output_path = Path(output_file)
    output_path.parent.mkdir(exist_ok=True, parents=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 결과 요약
    print("="*80)
    print("✅ 추출 완료!")
    print("="*80)
    print(f"\n📊 추출 결과 요약:")
    print(f"   🏢 매장명: {store_info['store_name']}")
    print(f"   📍 주소: {store_info['address']}")
    print(f"   📞 전화: {store_info['phone']}")
    print(f"   🛍️  총 상품: {len(products)}개")
    print(f"   📦 카테고리: {len(categorized)}개")
    print(f"   🏬 주변 매장: {len(nearby_stores)}개")
    print(f"\n💾 저장 위치: {output_file}")
    
    # 상품 통계
    stock_available = sum(1 for p in products if p['stock_status'] == '재고있음')
    stock_out = sum(1 for p in products if p['stock_status'] == '품절')
    
    print(f"\n📈 재고 현황:")
    print(f"   ✅ 재고있음: {stock_available}개")
    print(f"   ❌ 품절: {stock_out}개")
    print(f"   ⚠️  확인필요: {len(products) - stock_available - stock_out}개")
    
    # 가격 통계
    if products:
        avg_original = sum(p['original_price'] for p in products) / len(products)
        avg_sale = sum(p['sale_price'] for p in products) / len(products)
        avg_discount = sum(p['discount_rate'] for p in products if p['discount_rate'] > 0)
        discount_count = sum(1 for p in products if p['discount_rate'] > 0)
        
        print(f"\n💰 가격 정보:")
        print(f"   평균 정가: {avg_original:,.0f}원")
        print(f"   평균 판매가: {avg_sale:,.0f}원")
        if discount_count > 0:
            print(f"   평균 할인율: {avg_discount/discount_count:.1f}%")
            print(f"   할인 상품: {discount_count}개")
    
    print("\n" + "="*80)
    print("✨ AI 쇼핑 어시스턴트가 이 데이터를 참조하여 답변할 수 있습니다!")
    print("="*80)


if __name__ == "__main__":
    main()

