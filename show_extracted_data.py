#!/usr/bin/env python3
"""추출된 데이터 요약 표시"""

import json

with open('data/oliveyoung_extracted.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("="*70)
print("📦 올리브영 추출 데이터 요약")
print("="*70)
print(f"매장: {data['store_name']}")
print(f"추출 시간: {data['crawled_at']}")
print(f"총 상품: {data['total_products']}개")
print(f"카테고리: {data['categories_count']}개")

print("\n" + "="*70)
print("📋 카테고리별 상품 목록")
print("="*70)

for category, products in data['categories'].items():
    print(f"\n🏷️  {category} ({len(products)}개)")
    print("-" * 70)
    for i, product in enumerate(products, 1):
        price_str = f"{product['price']:,}원" if product['price'] > 0 else "가격 미표시"
        print(f"{i}. {product['name'][:60]}")
        print(f"   💰 가격: {price_str}")
        if product['brand']:
            print(f"   🏢 브랜드: {product['brand']}")
        if product['image_url']:
            print(f"   🖼️  이미지: {product['image_url'][:60]}...")
        print()

print("="*70)
print("✅ 데이터 파일: data/oliveyoung_extracted.json")
print("="*70)

