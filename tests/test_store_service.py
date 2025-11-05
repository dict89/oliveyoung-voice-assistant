"""
매장 서비스 테스트
"""
import pytest
from pathlib import Path
import sys

# 상위 디렉토리를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.store_service import StoreService


@pytest.fixture
def store_service():
    """StoreService 인스턴스를 생성합니다."""
    return StoreService()


def test_find_store_by_name(store_service):
    """매장 이름으로 검색 테스트"""
    store = store_service.find_store_by_name("강남")
    assert store is not None
    assert "강남" in store["name"]


def test_find_store_by_location(store_service):
    """위치로 매장 검색 테스트"""
    stores = store_service.find_store_by_location("강남")
    assert len(stores) > 0
    assert any("강남" in store["name"] or "강남" in store["address"] for store in stores)


def test_find_nearest_store(store_service):
    """랜드마크로 근처 매장 찾기 테스트"""
    store = store_service.find_nearest_store("강남역")
    assert store is not None
    assert any("강남역" in landmark for landmark in store["nearby_landmarks"])


def test_get_store_info(store_service):
    """매장 ID로 정보 조회 테스트"""
    store = store_service.get_store_info("D176")
    assert store is not None
    assert store["store_id"] == "D176"


def test_format_store_info(store_service):
    """매장 정보 포맷팅 테스트"""
    store = store_service.get_store_info("D176")
    
    # Brief 포맷
    brief = store_service.format_store_info(store, "brief")
    assert store["name"] in brief
    assert store["address"] in brief
    
    # Full 포맷
    full = store_service.format_store_info(store, "full")
    assert store["name"] in full
    assert "영업시간" in full


def test_search_by_service(store_service):
    """서비스로 매장 검색 테스트"""
    stores = store_service.search_by_service("화장품")
    assert len(stores) > 0
    
    stores = store_service.search_by_service("면세")
    assert len(stores) > 0
    assert any("면세" in str(store.get("services", [])) for store in stores)


def test_get_brand_info(store_service):
    """브랜드 정보 조회 테스트"""
    korean_brands = store_service.get_brand_info("korean")
    assert len(korean_brands) > 0
    assert "설화수" in korean_brands or "이니스프리" in korean_brands
    
    international_brands = store_service.get_brand_info("international")
    assert len(international_brands) > 0
    
    all_brands = store_service.get_brand_info("all")
    assert len(all_brands) == len(korean_brands) + len(international_brands)


def test_get_categories(store_service):
    """카테고리 정보 조회 테스트"""
    categories = store_service.get_categories()
    assert "skincare" in categories
    assert "makeup" in categories
    assert len(categories["skincare"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

