"""
올리브영 웹사이트 크롤러
매장 정보 및 상품 재고 정보를 수집합니다.
"""
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, Browser
import re


class OliveYoungCrawler:
    """올리브영 웹사이트 크롤러"""
    
    BASE_URL = "https://www.oliveyoung.co.kr"
    STORE_INFO_URL = f"{BASE_URL}/store/store/getStoreInfoMain.do"
    
    def __init__(self, output_dir: str = "data"):
        """
        Args:
            output_dir: 크롤링 데이터를 저장할 디렉토리
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    async def init_browser(self, headless: bool = True):
        """브라우저 초기화"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=headless)
        context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        self.page = await context.new_page()
        
    async def close_browser(self):
        """브라우저 종료"""
        if self.browser:
            await self.browser.close()
    
    async def get_store_list(self) -> List[Dict]:
        """
        올리브영 전체 매장 목록을 가져옵니다.
        
        Returns:
            매장 정보 리스트
        """
        print("📍 매장 목록을 가져오는 중...")
        
        try:
            await self.page.goto(self.STORE_INFO_URL, wait_until="networkidle")
            await asyncio.sleep(2)  # 페이지 로딩 대기
            
            # 페이지 소스 가져오기
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            stores = []
            
            # 매장 목록 찾기 (실제 HTML 구조에 맞게 조정 필요)
            # 올리브영 웹사이트의 실제 구조를 확인한 후 수정해야 합니다
            store_elements = soup.select('.store-item, .storeInfo, li.store')
            
            for element in store_elements:
                try:
                    store_name = element.select_one('.store-name, .storeName, h3, .title')
                    store_addr = element.select_one('.store-address, .address, .addr')
                    store_id = element.get('data-store-id') or element.get('data-id')
                    
                    if store_name:
                        stores.append({
                            'store_id': store_id or '',
                            'name': store_name.text.strip(),
                            'address': store_addr.text.strip() if store_addr else '',
                        })
                except Exception as e:
                    print(f"매장 정보 파싱 오류: {e}")
                    continue
            
            print(f"✅ {len(stores)}개 매장 정보를 가져왔습니다.")
            return stores
            
        except Exception as e:
            print(f"❌ 매장 목록 가져오기 실패: {e}")
            return []
    
    async def search_store_by_name(self, store_name: str) -> Optional[str]:
        """
        매장명으로 검색하여 매장 코드를 찾습니다.
        
        Args:
            store_name: 검색할 매장명 (예: "명동 타운")
            
        Returns:
            매장 코드 또는 None
        """
        print(f"🔍 '{store_name}' 매장을 검색 중...")
        
        try:
            await self.page.goto(self.STORE_INFO_URL, wait_until="networkidle")
            
            # 검색창 찾기 및 입력
            search_input = await self.page.query_selector('input[name="storeName"], input#searchKeyword, input.search-input')
            if search_input:
                await search_input.fill(store_name)
                await asyncio.sleep(1)
                
                # 검색 버튼 클릭 또는 엔터
                search_btn = await self.page.query_selector('button.search-btn, button[type="submit"]')
                if search_btn:
                    await search_btn.click()
                else:
                    await search_input.press('Enter')
                
                await asyncio.sleep(2)
            
            # 검색 결과에서 첫 번째 매장 선택
            store_link = await self.page.query_selector('.store-item:first-child, .storeInfo:first-child')
            if store_link:
                store_code = await store_link.get_attribute('data-store-id')
                print(f"✅ 매장 코드: {store_code}")
                return store_code
            
        except Exception as e:
            print(f"❌ 매장 검색 실패: {e}")
        
        return None
    
    async def get_store_products(self, store_name: str = "명동 타운", 
                                 categories: List[str] = None) -> Dict:
        """
        특정 매장의 상품 정보를 가져옵니다.
        
        Args:
            store_name: 매장명
            categories: 크롤링할 카테고리 목록 (None이면 전체)
            
        Returns:
            상품 정보 딕셔너리
        """
        print(f"🛍️  '{store_name}' 매장의 상품 정보를 수집 중...")
        
        products = {
            'store_name': store_name,
            'crawled_at': datetime.now().isoformat(),
            'categories': {}
        }
        
        try:
            # 매장 페이지로 이동
            await self.page.goto(self.STORE_INFO_URL, wait_until="networkidle")
            
            # 매장 검색 및 선택
            store_code = await self.search_store_by_name(store_name)
            if not store_code:
                print("⚠️  매장을 찾을 수 없습니다. 수동 탐색을 시도합니다...")
            
            # "재고조회" 또는 "상품보기" 버튼 클릭
            await asyncio.sleep(2)
            
            # 방법 1: 재고 조회 버튼 찾기
            inventory_btn = await self.page.query_selector(
                'button:has-text("재고"), a:has-text("재고"), .inventory-btn'
            )
            if inventory_btn:
                await inventory_btn.click()
                await asyncio.sleep(3)
            
            # 카테고리별 상품 수집
            default_categories = [
                '스킨케어', '메이크업', '마스크/팩', '클렌징', 
                '선케어', '헤어케어', '바디케어', '남성케어'
            ]
            
            target_categories = categories or default_categories
            
            for category in target_categories:
                print(f"  📦 '{category}' 카테고리 수집 중...")
                category_products = await self._get_category_products(category)
                products['categories'][category] = category_products
                await asyncio.sleep(1)
            
            # 결과 저장
            output_file = self.output_dir / f"products_{store_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 상품 정보가 저장되었습니다: {output_file}")
            
        except Exception as e:
            print(f"❌ 상품 정보 수집 실패: {e}")
        
        return products
    
    async def _get_category_products(self, category_name: str) -> List[Dict]:
        """
        특정 카테고리의 상품 정보를 가져옵니다.
        
        Args:
            category_name: 카테고리명
            
        Returns:
            상품 정보 리스트
        """
        products = []
        
        try:
            # 카테고리 선택 (실제 웹사이트 구조에 맞게 수정 필요)
            category_btn = await self.page.query_selector(f'button:has-text("{category_name}"), a:has-text("{category_name}")')
            if category_btn:
                await category_btn.click()
                await asyncio.sleep(2)
            
            # 페이지 스크롤 (동적 로딩 대응)
            await self._scroll_page()
            
            # 상품 목록 가져오기
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # 상품 요소 찾기 (실제 HTML 구조에 맞게 조정)
            product_elements = soup.select('.product-item, .prd_item, .goods-item, li.item')
            
            for element in product_elements:
                try:
                    product = await self._parse_product_element(element)
                    if product:
                        products.append(product)
                except Exception as e:
                    print(f"    상품 파싱 오류: {e}")
                    continue
            
            print(f"    ✅ {len(products)}개 상품 수집 완료")
            
        except Exception as e:
            print(f"    ❌ 카테고리 '{category_name}' 수집 실패: {e}")
        
        return products
    
    async def _parse_product_element(self, element) -> Optional[Dict]:
        """
        상품 요소를 파싱하여 상품 정보를 추출합니다.
        
        Args:
            element: BeautifulSoup 요소
            
        Returns:
            상품 정보 딕셔너리
        """
        try:
            # 상품명
            name_elem = element.select_one('.prd-name, .prod_name, .product-name, .name, h3, .title')
            name = name_elem.text.strip() if name_elem else None
            
            # 가격
            price_elem = element.select_one('.price, .prd-price, .sale-price, .cost')
            price_text = price_elem.text.strip() if price_elem else "0"
            price = int(re.sub(r'[^\d]', '', price_text)) if price_text else 0
            
            # 이미지
            img_elem = element.select_one('img')
            image_url = img_elem.get('src') or img_elem.get('data-src') if img_elem else None
            if image_url and not image_url.startswith('http'):
                image_url = self.BASE_URL + image_url
            
            # 브랜드
            brand_elem = element.select_one('.brand, .prd-brand, .brand-name')
            brand = brand_elem.text.strip() if brand_elem else None
            
            # 재고 상태
            stock_elem = element.select_one('.stock, .stock-status, .inventory')
            stock_status = stock_elem.text.strip() if stock_elem else "재고 확인 필요"
            
            # 상품 코드
            product_id = element.get('data-product-id') or element.get('data-goods-no')
            
            if name:
                return {
                    'product_id': product_id or '',
                    'name': name,
                    'brand': brand or '',
                    'price': price,
                    'image_url': image_url or '',
                    'stock_status': stock_status,
                }
        
        except Exception as e:
            print(f"      파싱 오류: {e}")
        
        return None
    
    async def _scroll_page(self, scroll_count: int = 3):
        """페이지를 스크롤하여 동적 콘텐츠를 로드합니다."""
        for i in range(scroll_count):
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1)
    
    async def get_product_detail(self, product_url: str) -> Dict:
        """
        상품 상세 페이지 정보를 가져옵니다.
        
        Args:
            product_url: 상품 상세 페이지 URL
            
        Returns:
            상세 정보 딕셔너리
        """
        try:
            await self.page.goto(product_url, wait_until="networkidle")
            await asyncio.sleep(2)
            
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # 상세 정보 추출
            detail = {
                'description': '',
                'ingredients': [],
                'how_to_use': '',
                'reviews_count': 0,
                'rating': 0.0,
            }
            
            # 상품 설명
            desc_elem = soup.select_one('.product-detail, .prd-detail, .description')
            if desc_elem:
                detail['description'] = desc_elem.text.strip()
            
            # 리뷰 수
            review_elem = soup.select_one('.review-count, .reviews-count')
            if review_elem:
                review_text = re.sub(r'[^\d]', '', review_elem.text)
                detail['reviews_count'] = int(review_text) if review_text else 0
            
            # 평점
            rating_elem = soup.select_one('.rating, .score, .star-score')
            if rating_elem:
                rating_text = re.findall(r'[\d.]+', rating_elem.text)
                detail['rating'] = float(rating_text[0]) if rating_text else 0.0
            
            return detail
            
        except Exception as e:
            print(f"상품 상세 정보 가져오기 실패: {e}")
            return {}
    
    async def crawl_all(self, store_names: List[str] = None):
        """
        여러 매장의 상품 정보를 일괄 크롤링합니다.
        
        Args:
            store_names: 매장명 리스트 (None이면 주요 매장만)
        """
        default_stores = ["명동 타운", "명동 중앙점", "강남역점", "홍대입구점"]
        target_stores = store_names or default_stores
        
        await self.init_browser(headless=False)  # 디버깅을 위해 브라우저 표시
        
        try:
            for store_name in target_stores:
                print(f"\n{'='*60}")
                print(f"🏪 {store_name} 매장 크롤링 시작")
                print(f"{'='*60}\n")
                
                await self.get_store_products(store_name)
                await asyncio.sleep(3)  # 요청 간격
                
        finally:
            await self.close_browser()
        
        print("\n✅ 모든 크롤링 작업이 완료되었습니다!")


async def main():
    """메인 실행 함수"""
    crawler = OliveYoungCrawler()
    
    # 명동 타운 매장 크롤링
    await crawler.init_browser(headless=False)
    try:
        await crawler.get_store_products(
            store_name="명동 타운",
            categories=['스킨케어', '메이크업', '마스크/팩']
        )
    finally:
        await crawler.close_browser()


if __name__ == "__main__":
    asyncio.run(main())

