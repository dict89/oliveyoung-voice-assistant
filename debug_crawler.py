#!/usr/bin/env python3
"""
올리브영 웹사이트 구조 분석 도구

이 스크립트는 올리브영 웹사이트의 HTML 구조를 분석하여
적절한 CSS 셀렉터를 찾는 데 도움을 줍니다.

사용법:
  python debug_crawler.py
"""

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json


class OliveYoungDebugger:
    """올리브영 웹사이트 구조 분석기"""
    
    STORE_INFO_URL = "https://www.oliveyoung.co.kr/store/store/getStoreInfoMain.do"
    
    def __init__(self):
        self.browser = None
        self.page = None
    
    async def init_browser(self):
        """브라우저 초기화"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)
        context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        self.page = await context.new_page()
    
    async def close_browser(self):
        """브라우저 종료"""
        if self.browser:
            await self.browser.close()
    
    async def analyze_store_page(self):
        """매장 페이지 구조 분석"""
        print("\n" + "="*70)
        print("🔍 올리브영 매장 페이지 구조 분석")
        print("="*70 + "\n")
        
        try:
            print("📄 페이지 로딩 중...")
            await self.page.goto(self.STORE_INFO_URL, wait_until="networkidle")
            await asyncio.sleep(3)
            
            # HTML 저장
            content = await self.page.content()
            with open('debug_store_page.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ HTML이 'debug_store_page.html'에 저장되었습니다.")
            
            # BeautifulSoup으로 분석
            soup = BeautifulSoup(content, 'html.parser')
            
            # 1. 검색 입력창 찾기
            print("\n" + "-"*70)
            print("🔎 검색 입력창 분석")
            print("-"*70)
            
            input_candidates = soup.find_all('input')
            print(f"총 {len(input_candidates)}개의 input 요소 발견:")
            
            for i, inp in enumerate(input_candidates[:10], 1):
                attrs = {k: v for k, v in inp.attrs.items() if k in ['id', 'name', 'class', 'placeholder', 'type']}
                if attrs:
                    print(f"{i}. {attrs}")
            
            # 2. 매장 목록 요소 찾기
            print("\n" + "-"*70)
            print("🏪 매장 목록 요소 분석")
            print("-"*70)
            
            # 다양한 가능성 시도
            store_selectors = [
                '.store-item',
                '.store-list li',
                '.storeInfo',
                'li[data-store-id]',
                '.list-store li',
                'div[class*="store"]',
                'ul.store li'
            ]
            
            for selector in store_selectors:
                elements = soup.select(selector)
                if elements:
                    print(f"✅ '{selector}' : {len(elements)}개 발견")
                    if len(elements) > 0:
                        print(f"   첫 번째 요소 미리보기:")
                        print(f"   {str(elements[0])[:200]}...")
                else:
                    print(f"❌ '{selector}' : 발견 안됨")
            
            # 3. 버튼 요소 찾기
            print("\n" + "-"*70)
            print("🔘 버튼 요소 분석")
            print("-"*70)
            
            buttons = soup.find_all(['button', 'a'], string=lambda text: text and ('재고' in text or '검색' in text or '조회' in text))
            print(f"재고/검색 관련 버튼 {len(buttons)}개 발견:")
            
            for i, btn in enumerate(buttons[:5], 1):
                print(f"{i}. 텍스트: '{btn.get_text(strip=True)}', 태그: {btn.name}, 클래스: {btn.get('class')}")
            
            # 4. 페이지의 주요 클래스명 추출
            print("\n" + "-"*70)
            print("📋 주요 클래스명 분석")
            print("-"*70)
            
            all_classes = set()
            for element in soup.find_all(class_=True):
                all_classes.update(element.get('class', []))
            
            store_related = [cls for cls in all_classes if 'store' in cls.lower()]
            product_related = [cls for cls in all_classes if any(word in cls.lower() for word in ['product', 'goods', 'item', 'prd'])]
            
            print(f"\n매장 관련 클래스 ({len(store_related)}개):")
            for cls in sorted(store_related)[:20]:
                print(f"  - .{cls}")
            
            print(f"\n상품 관련 클래스 ({len(product_related)}개):")
            for cls in sorted(product_related)[:20]:
                print(f"  - .{cls}")
            
            # 5. 대화형 탐색 모드
            print("\n" + "="*70)
            print("💡 브라우저 창이 열려 있습니다.")
            print("   웹사이트를 직접 탐색하며 개발자 도구를 사용해보세요.")
            print("   F12를 눌러 개발자 도구를 열고 요소를 검사하세요.")
            print("   종료하려면 Ctrl+C를 누르세요.")
            print("="*70)
            
            # 사용자가 Ctrl+C를 누를 때까지 대기
            await asyncio.sleep(3600)  # 1시간 대기
            
        except KeyboardInterrupt:
            print("\n\n⚠️  사용자가 중단했습니다.")
        
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_search_functionality(self, search_term: str = "명동"):
        """검색 기능 테스트"""
        print(f"\n🔍 '{search_term}' 검색 테스트 중...")
        
        try:
            await self.page.goto(self.STORE_INFO_URL, wait_until="networkidle")
            await asyncio.sleep(2)
            
            # 다양한 셀렉터 시도
            search_selectors = [
                'input[name="storeName"]',
                'input#searchKeyword',
                'input.search-input',
                'input[placeholder*="매장"]',
                'input[type="text"]'
            ]
            
            for selector in search_selectors:
                element = await self.page.query_selector(selector)
                if element:
                    print(f"✅ 검색창 발견: {selector}")
                    await element.fill(search_term)
                    await asyncio.sleep(1)
                    
                    # 검색 버튼 찾기
                    search_buttons = [
                        'button[type="submit"]',
                        'button.search-btn',
                        'button:has-text("검색")'
                    ]
                    
                    for btn_selector in search_buttons:
                        btn = await self.page.query_selector(btn_selector)
                        if btn:
                            print(f"✅ 검색 버튼 발견: {btn_selector}")
                            await btn.click()
                            break
                    else:
                        await element.press('Enter')
                        print("⏎ Enter 키 입력")
                    
                    await asyncio.sleep(3)
                    
                    # 검색 결과 확인
                    content = await self.page.content()
                    if search_term in content:
                        print(f"✅ 검색 결과에 '{search_term}'이 포함되어 있습니다.")
                    
                    # 스크린샷 저장
                    await self.page.screenshot(path='debug_search_result.png')
                    print("📸 스크린샷이 'debug_search_result.png'에 저장되었습니다.")
                    
                    return True
            
            print("❌ 검색창을 찾을 수 없습니다.")
            return False
            
        except Exception as e:
            print(f"❌ 검색 테스트 실패: {e}")
            return False
    
    async def analyze_product_structure(self):
        """상품 페이지 구조 분석"""
        print("\n" + "="*70)
        print("🛍️  상품 페이지 구조 분석")
        print("="*70 + "\n")
        
        # 올리브영 메인 페이지의 상품 목록으로 이동
        try:
            await self.page.goto("https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100010001", 
                                wait_until="networkidle")
            await asyncio.sleep(3)
            
            # 페이지 스크롤하여 더 많은 상품 로드
            for _ in range(3):
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(1)
            
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # HTML 저장
            with open('debug_product_page.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ HTML이 'debug_product_page.html'에 저장되었습니다.")
            
            # 상품 요소 찾기
            product_selectors = [
                '.prd_item',
                '.prod-item',
                '.product-item',
                'li[class*="prd"]',
                'li[class*="prod"]',
                '.goods-item',
                'ul.cate_prd_list li'
            ]
            
            print("\n상품 요소 검색 결과:")
            for selector in product_selectors:
                elements = soup.select(selector)
                if elements:
                    print(f"✅ '{selector}' : {len(elements)}개 발견")
                    
                    if len(elements) > 0:
                        first = elements[0]
                        
                        # 상품명
                        name_elem = first.select_one('.prod_name, .prd-name, .product-name, .name')
                        if name_elem:
                            print(f"   상품명: {name_elem.get_text(strip=True)[:50]}")
                        
                        # 가격
                        price_elem = first.select_one('.price, .prd-price, .cost')
                        if price_elem:
                            print(f"   가격: {price_elem.get_text(strip=True)}")
                        
                        # 이미지
                        img_elem = first.select_one('img')
                        if img_elem:
                            print(f"   이미지: {img_elem.get('src', '')[:50]}")
                        
                        print()
            
            # 스크린샷 저장
            await self.page.screenshot(path='debug_products.png', full_page=True)
            print("📸 전체 페이지 스크린샷이 'debug_products.png'에 저장되었습니다.")
            
        except Exception as e:
            print(f"❌ 상품 페이지 분석 실패: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """메인 함수"""
    debugger = OliveYoungDebugger()
    
    try:
        await debugger.init_browser()
        
        # 1. 매장 페이지 구조 분석
        await debugger.analyze_store_page()
        
        # 2. 검색 기능 테스트 (주석 해제하여 사용)
        # await debugger.test_search_functionality("명동")
        
        # 3. 상품 페이지 구조 분석 (주석 해제하여 사용)
        # await debugger.analyze_product_structure()
        
    finally:
        await debugger.close_browser()


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║        올리브영 웹사이트 구조 분석 도구                          ║
║                                                                   ║
║  이 도구는 올리브영 웹사이트의 HTML 구조를 분석하여              ║
║  크롤러에 필요한 CSS 셀렉터를 찾는 데 도움을 줍니다.             ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())

