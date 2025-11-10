#!/usr/bin/env python3
"""
올리브영 웹사이트 실제 크롤러
매장 정보와 상품 재고 정보를 수집합니다.
"""

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
from datetime import datetime

async def crawl_oliveyoung_store(store_name="명동 타운"):
    """올리브영 매장 크롤링"""
    
    print(f"\n{'='*70}")
    print(f"🛍️  올리브영 '{store_name}' 매장 크롤링 시작")
    print(f"{'='*70}\n")
    
    async with async_playwright() as p:
        # 브라우저 시작
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # 매장 안내 페이지로 이동
            url = "https://www.oliveyoung.co.kr/store/store/getStoreInfoMain.do"
            print(f"📄 페이지 로딩: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print("⏳ 페이지 로딩 대기 중...")
            await asyncio.sleep(5)
            
            # 매장 목록 확인
            print("\n🔍 매장 목록에서 검색 중...")
            
            # 매장 리스트가 보일 때까지 대기
            await page.wait_for_selector('#storeList', timeout=10000)
            
            # 페이지 스크롤하여 모든 매장 로드
            for _ in range(3):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(1)
            
            # 매장 찾기
            stores = await page.query_selector_all('#storeList li._openYStore')
            print(f"✅ 총 {len(stores)}개 매장 발견")
            
            target_store = None
            store_element = None
            
            # 매장명으로 검색
            for store in stores:
                text = await store.inner_text()
                if store_name in text:
                    target_store = text.split('\n')[0]  # 첫 줄이 매장명
                    store_element = store
                    print(f"✅ '{target_store}' 매장 찾음!")
                    break
            
            if not store_element:
                print(f"❌ '{store_name}' 매장을 찾을 수 없습니다.")
                print(f"\n💡 사용 가능한 매장:")
                for i, store in enumerate(stores[:10], 1):
                    text = await store.inner_text()
                    name = text.split('\n')[0]
                    print(f"  {i}. {name}")
                await browser.close()
                return None
            
            # 매장 클릭
            print(f"\n🖱️  '{target_store}' 매장 클릭...")
            await store_element.click()
            await asyncio.sleep(3)
            
            # 매장 상세 정보 가져오기
            print("\n📋 매장 상세 정보 수집 중...")
            
            # 매장 상세 영역이 표시될 때까지 대기
            await page.wait_for_selector('#storeDetail', state='visible', timeout=10000)
            
            # 매장 정보 추출
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            store_detail = soup.find('div', id='storeDetail')
            if store_detail:
                # 매장 기본 정보
                store_data = {
                    'store_name': target_store,
                    'crawled_at': datetime.now().isoformat(),
                    'address': '',
                    'phone': '',
                    'operating_hours': {},
                    'services': [],
                    'images': []
                }
                
                # 주소
                addr_elem = store_detail.select_one('.txt_addr, .store_desc .txt')
                if addr_elem:
                    store_data['address'] = addr_elem.get_text(strip=True)
                
                # 전화번호
                phone_elem = store_detail.select_one('.txt_phone, [href^="tel:"]')
                if phone_elem:
                    store_data['phone'] = phone_elem.get_text(strip=True)
                
                # 영업시간
                hours_elems = store_detail.select('.txt_status, .time')
                for elem in hours_elems:
                    text = elem.get_text(strip=True)
                    if '~' in text or ':' in text:
                        store_data['operating_hours']['info'] = text
                
                # 이미지
                img_elems = store_detail.select('img')
                for img in img_elems[:5]:  # 최대 5개
                    src = img.get('src')
                    if src and 'oliveyoung.co.kr' in src:
                        store_data['images'].append(src)
                
                print(f"✅ 매장 정보 수집 완료")
                print(f"   주소: {store_data['address'][:50]}...")
                print(f"   전화: {store_data['phone']}")
                
            # 재고 조회 버튼 찾기
            print("\n🔍 재고 조회 시도...")
            
            # 재고 조회 관련 버튼 찾기 (여러 가능성 시도)
            stock_selectors = [
                'text="재고"',
                'text="재고 조회"',
                'text="재고확인"',
                '.btn_stock',
                'button:has-text("재고")',
                'a:has-text("재고")'
            ]
            
            stock_button = None
            for selector in stock_selectors:
                try:
                    stock_button = await page.query_selector(selector)
                    if stock_button:
                        print(f"✅ 재고 조회 버튼 발견: {selector}")
                        break
                except:
                    continue
            
            if stock_button:
                await stock_button.click()
                print("🖱️  재고 조회 버튼 클릭")
                await asyncio.sleep(5)
                
                # 재고 조회 영역이 로드될 때까지 대기
                try:
                    await page.wait_for_selector('#storeStockMain', state='visible', timeout=10000)
                    print("✅ 재고 조회 페이지 로드 완료")
                except:
                    print("⚠️  재고 조회 페이지 로딩 타임아웃 (계속 진행)")
                
                # 카테고리별 상품 수집
                all_products = []
                categories_to_crawl = ['스킨케어', '메이크업', '마스크/팩']  # 예시 카테고리
                
                print(f"\n📋 {len(categories_to_crawl)}개 카테고리 크롤링 시작...")
                
                for cat_idx, category in enumerate(categories_to_crawl, 1):
                    print(f"\n[{cat_idx}/{len(categories_to_crawl)}] 📦 '{category}' 카테고리 수집 중...")
                    
                    try:
                        # 카테고리 버튼 찾기 및 클릭
                        category_button = await page.query_selector(f'button:has-text("{category}")')
                        
                        if category_button:
                            await category_button.click()
                            print(f"  🖱️  '{category}' 버튼 클릭")
                            await asyncio.sleep(3)  # 상품 로딩 대기
                            
                            # 페이지 스크롤하여 더 많은 상품 로드
                            for _ in range(2):
                                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                                await asyncio.sleep(1)
                            
                            # 상품 목록 가져오기
                            content = await page.content()
                            soup = BeautifulSoup(content, 'html.parser')
                            
                            # 상품 리스트 영역 찾기
                            product_list = soup.select('#stockGoodsList li, #goodsList li, .list_store_prdt li')
                            
                            print(f"  ✅ {len(product_list)}개 상품 발견")
                            
                            for idx, product_elem in enumerate(product_list[:10], 1):  # 카테고리당 최대 10개
                                try:
                                    # 상품 링크에서 정보 추출
                                    link_elem = product_elem.select_one('a')
                                    if not link_elem:
                                        continue
                                    
                                    # 이미지
                                    img_elem = product_elem.select_one('img')
                                    image_url = ""
                                    if img_elem:
                                        image_url = img_elem.get('src') or img_elem.get('data-src') or ""
                                        if image_url and not image_url.startswith('http'):
                                            image_url = 'https://www.oliveyoung.co.kr' + image_url
                                    
                                    # onclick 속성에서 상품명 추출
                                    onclick = link_elem.get('onclick', '')
                                    product_name = ""
                                    if 'storeInfos' in onclick:
                                        # onclick="storeInfos.storeStockMain.getProductStockDetail('상품코드', '상품명', ...)"
                                        import re
                                        match = re.search(r"'([^']+)',\s*'([^']+)'", onclick)
                                        if match:
                                            product_name = match.group(2)
                                    
                                    # 텍스트에서 상품명 추출 (fallback)
                                    if not product_name:
                                        text_elem = product_elem.select_one('.tit, .name, .product-name')
                                        if text_elem:
                                            product_name = text_elem.get_text(strip=True)
                                    
                                    # 전체 텍스트에서 정보 추출
                                    full_text = product_elem.get_text(strip=True)
                                    
                                    # 가격 추출
                                    price = 0
                                    price_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*원', full_text)
                                    if price_match:
                                        price = int(price_match.group(1).replace(',', ''))
                                    
                                    # 재고 상태 추출
                                    stock_status = "확인 필요"
                                    if '재고있음' in full_text or '재고 있음' in full_text:
                                        stock_status = "재고있음"
                                    elif '품절' in full_text or '재고없음' in full_text:
                                        stock_status = "품절"
                                    
                                    if product_name:
                                        product = {
                                            'category': category,
                                            'name': product_name,
                                            'price': price,
                                            'image_url': image_url,
                                            'stock_status': stock_status
                                        }
                                        all_products.append(product)
                                        print(f"    {idx}. {product_name[:40]}... - {price:,}원 ({stock_status})")
                                
                                except Exception as e:
                                    continue
                        
                        else:
                            print(f"  ⚠️  '{category}' 버튼을 찾을 수 없습니다.")
                    
                    except Exception as e:
                        print(f"  ❌ '{category}' 크롤링 오류: {e}")
                        continue
                
                store_data['products'] = all_products
                print(f"\n✅ 총 {len(all_products)}개 상품 수집 완료")
            
            else:
                print("⚠️  재고 조회 버튼을 찾을 수 없습니다.")
                print("💡 매장 상세 정보만 저장합니다.")
                store_data['products'] = []
            
            # 결과 저장
            output_file = f"data/oliveyoung_{target_store.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(store_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n{'='*70}")
            print(f"✅ 크롤링 완료!")
            print(f"📁 저장 위치: {output_file}")
            print(f"{'='*70}\n")
            
            # 브라우저 잠시 유지 (결과 확인용)
            print("💡 10초 후 브라우저가 자동으로 닫힙니다...")
            await asyncio.sleep(10)
            
            await browser.close()
            return store_data
        
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            await browser.close()
            return None

if __name__ == "__main__":
    import sys
    
    store_name = "명동 타운"
    if len(sys.argv) > 1:
        store_name = sys.argv[1]
    
    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║              올리브영 매장 크롤러 (실제 구조 기반)               ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(crawl_oliveyoung_store(store_name))

