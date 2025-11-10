#!/usr/bin/env python3
"""
올리브영 웹사이트 간단 테스트 크롤러
실제 페이지 구조를 확인합니다.
"""

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json

async def test_oliveyoung():
    print("🔍 올리브영 웹사이트 구조 분석 시작...\n")
    
    async with async_playwright() as p:
        # 브라우저 시작
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # 매장 안내 페이지로 이동
            url = "https://www.oliveyoung.co.kr/store/store/getStoreInfoMain.do"
            print(f"📄 페이지 로딩: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print("⏳ 페이지 콘텐츠 로딩 대기 중...")
            await asyncio.sleep(5)
            
            # 페이지 제목 확인
            title = await page.title()
            print(f"✅ 페이지 제목: {title}\n")
            
            # HTML 저장
            content = await page.content()
            with open('oliveyoung_store_page.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ HTML 저장: oliveyoung_store_page.html\n")
            
            # BeautifulSoup으로 파싱
            soup = BeautifulSoup(content, 'html.parser')
            
            # 1. 검색 입력창 찾기
            print("="*70)
            print("🔎 검색 입력창 분석")
            print("="*70)
            inputs = soup.find_all('input', limit=10)
            for i, inp in enumerate(inputs, 1):
                print(f"{i}. type={inp.get('type', 'N/A')}, name={inp.get('name', 'N/A')}, "
                      f"id={inp.get('id', 'N/A')}, placeholder={inp.get('placeholder', 'N/A')}")
            
            # 2. 주요 클래스명 수집
            print("\n" + "="*70)
            print("📋 주요 클래스명 (store 관련)")
            print("="*70)
            all_classes = set()
            for element in soup.find_all(class_=True):
                all_classes.update(element.get('class', []))
            
            store_related = sorted([cls for cls in all_classes if 'store' in cls.lower()])[:20]
            for cls in store_related:
                print(f"  - {cls}")
            
            # 3. 주요 ID 수집
            print("\n" + "="*70)
            print("🆔 주요 ID (store 관련)")
            print("="*70)
            all_ids = [elem.get('id') for elem in soup.find_all(id=True) if elem.get('id')]
            store_ids = sorted([id_val for id_val in all_ids if 'store' in id_val.lower()])[:20]
            for id_val in store_ids:
                print(f"  - {id_val}")
            
            # 4. 링크와 버튼 찾기
            print("\n" + "="*70)
            print("🔗 주요 링크/버튼")
            print("="*70)
            links = soup.find_all(['a', 'button'], limit=20)
            for i, link in enumerate(links, 1):
                text = link.get_text(strip=True)[:50]
                if text:
                    print(f"{i}. {link.name}: {text}")
            
            # 스크린샷 저장
            await page.screenshot(path='oliveyoung_store_page.png', full_page=True)
            print("\n✅ 스크린샷 저장: oliveyoung_store_page.png")
            
            print("\n" + "="*70)
            print("💡 브라우저 창이 열려 있습니다.")
            print("   직접 페이지를 탐색해보세요.")
            print("   F12를 눌러 개발자 도구를 사용할 수 있습니다.")
            print("   종료하려면 Ctrl+C를 누르세요.")
            print("="*70)
            
            # 10초간 유지
            await asyncio.sleep(10)
            
        except KeyboardInterrupt:
            print("\n⚠️ 사용자가 중단했습니다.")
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()
            print("\n✅ 분석 완료!")

if __name__ == "__main__":
    asyncio.run(test_oliveyoung())

