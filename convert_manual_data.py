#!/usr/bin/env python3
"""
수동으로 추출한 올리브영 데이터를 정리하는 스크립트

사용법:
  python3 convert_manual_data.py input.json output.json
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def clean_product_data(raw_product):
    """원시 상품 데이터를 정리"""
    return {
        'product_id': raw_product.get('product_id', ''),
        'name': raw_product.get('name', '').strip(),
        'brand': raw_product.get('brand', '').strip(),
        'price': int(raw_product.get('price', 0)),
        'image_url': raw_product.get('image_url', ''),
        'stock_status': raw_product.get('stock_status', '확인 필요'),
        'description': raw_product.get('description', '')
    }


def convert_manual_data(input_file, output_file):
    """
    수동 추출 데이터를 표준 형식으로 변환
    
    입력 형식 (예시):
    {
        "category": "스킨케어",
        "products": [...]
    }
    
    또는:
    [
        {"name": "...", "price": ...},
        ...
    ]
    """
    print(f"📂 입력 파일 로드 중: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    # 데이터 구조 확인
    if isinstance(raw_data, list):
        # 단순 리스트 형식
        print("📋 단순 리스트 형식 감지")
        products = raw_data
        category = "기타"
    elif isinstance(raw_data, dict):
        if 'products' in raw_data:
            # {category: "...", products: [...]} 형식
            print("📦 카테고리 포함 형식 감지")
            products = raw_data['products']
            category = raw_data.get('category', '기타')
        elif 'categories' in raw_data:
            # 이미 표준 형식
            print("✅ 이미 표준 형식입니다")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(raw_data, f, ensure_ascii=False, indent=2)
            return
        else:
            print("❌ 알 수 없는 형식입니다")
            return
    else:
        print("❌ 지원하지 않는 데이터 타입")
        return
    
    # 데이터 정리
    print(f"🔧 {len(products)}개 상품 정리 중...")
    
    cleaned_products = []
    for idx, product in enumerate(products, 1):
        try:
            if product.get('name'):  # 상품명이 있는 것만
                cleaned = clean_product_data(product)
                cleaned_products.append(cleaned)
        except Exception as e:
            print(f"  ⚠️  상품 {idx} 정리 실패: {e}")
    
    # 표준 형식으로 변환
    result = {
        'store_name': '올리브영 명동 타운',
        'store_id': 'D101',
        'crawled_at': datetime.now().isoformat(),
        'categories': {
            category: cleaned_products
        },
        'total_products': len(cleaned_products),
        'categories_count': 1
    }
    
    # 저장
    print(f"💾 출력 파일 저장 중: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 결과 요약
    print("\n" + "="*70)
    print("✅ 변환 완료!")
    print("="*70)
    print(f"카테고리: {category}")
    print(f"총 상품: {len(cleaned_products)}개")
    print(f"\n상품 목록 (처음 5개):")
    for i, p in enumerate(cleaned_products[:5], 1):
        print(f"  {i}. {p['name'][:50]}... - {p['price']:,}원 ({p['stock_status']})")
    
    if len(cleaned_products) > 5:
        print(f"  ... 외 {len(cleaned_products) - 5}개")
    
    print(f"\n📁 저장 위치: {output_file}")


def merge_multiple_categories(input_files, output_file):
    """
    여러 카테고리 파일을 하나로 합치기
    
    사용법:
      python3 convert_manual_data.py --merge skincare.json makeup.json output.json
    """
    print(f"🔄 {len(input_files)}개 파일 병합 중...")
    
    merged_data = {
        'store_name': '올리브영 명동 타운',
        'store_id': 'D101',
        'crawled_at': datetime.now().isoformat(),
        'categories': {},
        'total_products': 0,
        'categories_count': 0
    }
    
    for file_path in input_files:
        print(f"\n📂 {file_path} 로드 중...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 카테고리 추출
        if isinstance(data, dict):
            if 'categories' in data:
                # 표준 형식
                for cat, products in data['categories'].items():
                    merged_data['categories'][cat] = products
                    print(f"  ✅ {cat}: {len(products)}개 상품")
            elif 'products' in data:
                # {category: "...", products: [...]} 형식
                cat = data.get('category', Path(file_path).stem)
                merged_data['categories'][cat] = data['products']
                print(f"  ✅ {cat}: {len(data['products'])}개 상품")
    
    # 통계 업데이트
    merged_data['categories_count'] = len(merged_data['categories'])
    merged_data['total_products'] = sum(
        len(products) for products in merged_data['categories'].values()
    )
    
    # 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)
    
    # 결과
    print("\n" + "="*70)
    print("✅ 병합 완료!")
    print("="*70)
    print(f"총 카테고리: {merged_data['categories_count']}개")
    print(f"총 상품: {merged_data['total_products']}개")
    print(f"\n카테고리별 상품 수:")
    for cat, products in merged_data['categories'].items():
        print(f"  - {cat}: {len(products)}개")
    print(f"\n📁 저장 위치: {output_file}")


def main():
    """메인 함수"""
    if len(sys.argv) < 3:
        print("""
올리브영 수동 데이터 변환 도구

사용법:
  # 단일 파일 변환
  python3 convert_manual_data.py input.json output.json
  
  # 여러 파일 병합
  python3 convert_manual_data.py --merge file1.json file2.json file3.json output.json

예시:
  python3 convert_manual_data.py data/raw_skincare.json data/skincare.json
  python3 convert_manual_data.py --merge data/skincare.json data/makeup.json data/all_products.json
        """)
        return
    
    # 병합 모드
    if sys.argv[1] == '--merge':
        if len(sys.argv) < 4:
            print("❌ 최소 2개 입력 파일과 1개 출력 파일이 필요합니다")
            return
        
        input_files = sys.argv[2:-1]
        output_file = sys.argv[-1]
        merge_multiple_categories(input_files, output_file)
    
    # 단일 변환 모드
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        
        if not Path(input_file).exists():
            print(f"❌ 입력 파일을 찾을 수 없습니다: {input_file}")
            return
        
        convert_manual_data(input_file, output_file)


if __name__ == "__main__":
    main()

