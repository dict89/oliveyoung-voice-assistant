#!/usr/bin/env python3
"""
올리브영 크롤러 실행 스크립트

사용 예시:
  python crawl.py --store "명동 타운"
  python crawl.py --stores "명동 타운,강남역점,홍대입구점"
  python crawl.py --store "명동 타운" --categories "스킨케어,메이크업" --headless
"""

import asyncio
import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.oliveyoung_crawler import OliveYoungCrawler


def parse_args():
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(
        description='올리브영 매장 상품 정보 크롤러',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  %(prog)s --store "명동 타운"
  %(prog)s --stores "명동 타운,강남역점,홍대입구점"
  %(prog)s --store "명동 타운" --categories "스킨케어,메이크업"
  %(prog)s --store "명동 타운" --headless
        """
    )
    
    # 매장 옵션
    store_group = parser.add_mutually_exclusive_group(required=True)
    store_group.add_argument(
        '--store',
        type=str,
        help='크롤링할 단일 매장명 (예: "명동 타운")'
    )
    store_group.add_argument(
        '--stores',
        type=str,
        help='크롤링할 여러 매장명 (쉼표로 구분, 예: "명동 타운,강남역점")'
    )
    
    # 카테고리 옵션
    parser.add_argument(
        '--categories',
        type=str,
        help='크롤링할 카테고리 (쉼표로 구분, 예: "스킨케어,메이크업")\n'
             '기본값: 전체 카테고리',
        default=None
    )
    
    # 브라우저 옵션
    parser.add_argument(
        '--headless',
        action='store_true',
        help='브라우저를 숨김 모드로 실행 (기본: 브라우저 표시)'
    )
    
    # 출력 디렉토리
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data',
        help='크롤링 데이터를 저장할 디렉토리 (기본: data)'
    )
    
    # 대기 시간
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='요청 사이 대기 시간 (초, 기본: 2.0)'
    )
    
    return parser.parse_args()


async def crawl_single_store(crawler: OliveYoungCrawler, 
                             store_name: str, 
                             categories: list = None):
    """단일 매장 크롤링"""
    print(f"\n{'='*70}")
    print(f"🏪 '{store_name}' 매장 크롤링 시작")
    print(f"{'='*70}\n")
    
    try:
        products = await crawler.get_store_products(
            store_name=store_name,
            categories=categories
        )
        
        # 결과 요약
        total_products = sum(len(items) for items in products['categories'].values())
        print(f"\n✅ '{store_name}' 크롤링 완료:")
        print(f"   - 총 카테고리: {len(products['categories'])}개")
        print(f"   - 총 상품: {total_products}개")
        
        for category, items in products['categories'].items():
            print(f"   - {category}: {len(items)}개")
        
        return products
        
    except Exception as e:
        print(f"\n❌ '{store_name}' 크롤링 실패: {e}")
        return None


async def crawl_multiple_stores(crawler: OliveYoungCrawler, 
                                store_names: list,
                                categories: list = None,
                                delay: float = 2.0):
    """여러 매장 크롤링"""
    results = []
    
    for i, store_name in enumerate(store_names, 1):
        print(f"\n[{i}/{len(store_names)}]")
        
        result = await crawl_single_store(crawler, store_name, categories)
        results.append(result)
        
        # 마지막 매장이 아니면 대기
        if i < len(store_names):
            print(f"\n⏳ {delay}초 대기 중...")
            await asyncio.sleep(delay)
    
    return results


async def main():
    """메인 실행 함수"""
    args = parse_args()
    
    # 카테고리 파싱
    categories = None
    if args.categories:
        categories = [cat.strip() for cat in args.categories.split(',')]
    
    # 크롤러 초기화
    crawler = OliveYoungCrawler(output_dir=args.output_dir)
    
    print("\n" + "="*70)
    print("🚀 올리브영 크롤러 시작")
    print("="*70)
    print(f"출력 디렉토리: {args.output_dir}")
    print(f"브라우저 모드: {'숨김' if args.headless else '표시'}")
    if categories:
        print(f"크롤링 카테고리: {', '.join(categories)}")
    else:
        print(f"크롤링 카테고리: 전체")
    print("="*70)
    
    # 브라우저 초기화
    await crawler.init_browser(headless=args.headless)
    
    try:
        # 단일 매장 크롤링
        if args.store:
            await crawl_single_store(crawler, args.store, categories)
        
        # 여러 매장 크롤링
        elif args.stores:
            store_names = [s.strip() for s in args.stores.split(',')]
            await crawl_multiple_stores(
                crawler, 
                store_names, 
                categories,
                delay=args.delay
            )
    
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 중단했습니다.")
    
    except Exception as e:
        print(f"\n\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 브라우저 종료
        await crawler.close_browser()
        print("\n" + "="*70)
        print("✅ 크롤링 작업 종료")
        print("="*70 + "\n")


if __name__ == "__main__":
    # Windows에서 이벤트 루프 정책 설정
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())

