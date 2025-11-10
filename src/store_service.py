"""
올리브영 매장 정보 서비스
매장 검색, 정보 조회, 추천 기능 제공
"""
import json
from pathlib import Path
from typing import List, Dict, Optional
import re


class StoreService:
    """올리브영 매장 정보를 관리하고 검색하는 서비스"""
    
    def __init__(self, data_path: str = "data/assistant_data.json"):
        """
        Args:
            data_path: 매장 데이터 JSON 파일 경로
        """
        self.data_path = Path(data_path)
        self.data = self._load_data()
        
    def _load_data(self) -> Dict:
        """매장 데이터를 로드합니다."""
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # assistant_data.json 구조에 맞게 변환
                return {
                    "store": data.get("store", {}),
                    "products": data.get("products", {}),
                    "nearby_stores": data.get("nearby_stores", []),
                    "stores": [data.get("store", {})] + data.get("nearby_stores", [])  # 호환성
                }
        except FileNotFoundError:
            print(f"Warning: {self.data_path} not found. Using empty data.")
            return {"store": {}, "products": {}, "nearby_stores": [], "stores": []}
    
    def find_store_by_name(self, name: str) -> Optional[Dict]:
        """
        매장 이름으로 검색합니다.
        
        Args:
            name: 검색할 매장 이름 (일부만 입력해도 가능)
            
        Returns:
            매장 정보 딕셔너리 또는 None
        """
        name_lower = name.lower()
        for store in self.data["stores"]:
            if name_lower in store["name"].lower():
                return store
        return None
    
    def find_store_by_location(self, location: str) -> List[Dict]:
        """
        지역/위치로 매장을 검색합니다.
        
        Args:
            location: 지역명 (예: "강남", "명동", "홍대")
            
        Returns:
            매장 정보 리스트
        """
        location_lower = location.lower()
        results = []
        
        for store in self.data["stores"]:
            # 매장명, 주소, 주변 랜드마크에서 검색
            search_fields = [
                store["name"],
                store["address"],
                *store.get("nearby_landmarks", [])
            ]
            
            if any(location_lower in field.lower() for field in search_fields):
                results.append(store)
        
        return results
    
    def find_nearest_store(self, landmark: str) -> Optional[Dict]:
        """
        특정 랜드마크 근처의 매장을 찾습니다.
        
        Args:
            landmark: 랜드마크명 (예: "강남역", "명동역")
            
        Returns:
            가장 가까운 매장 정보 또는 None
        """
        landmark_lower = landmark.lower()
        
        for store in self.data["stores"]:
            nearby = store.get("nearby_landmarks", [])
            if any(landmark_lower in mark.lower() for mark in nearby):
                return store
        
        return None
    
    def get_store_info(self, store_id: str) -> Optional[Dict]:
        """
        매장 ID로 정보를 조회합니다.
        
        Args:
            store_id: 매장 ID (예: "D176")
            
        Returns:
            매장 정보 딕셔너리 또는 None
        """
        for store in self.data["stores"]:
            if store["store_id"] == store_id:
                return store
        return None
    
    def format_store_info(self, store: Dict, detail_level: str = "full") -> str:
        """
        매장 정보를 사용자 친화적인 텍스트로 포맷팅합니다.
        
        Args:
            store: 매장 정보 딕셔너리
            detail_level: 상세 수준 ("brief", "medium", "full")
            
        Returns:
            포맷팅된 텍스트
        """
        if not store:
            return "매장 정보를 찾을 수 없습니다."
        
        # 기본 정보 (항상 포함)
        result = f"✨ {store['name']}\n"
        result += f"📍 주소: {store['address']}\n"
        result += f"📞 전화: {store['phone']}\n"
        
        if detail_level == "brief":
            return result
        
        # 중간 상세 정보
        hours = store.get("operating_hours", {})
        result += f"⏰ 영업시간:\n"
        result += f"   평일: {hours.get('weekday', '정보 없음')}\n"
        result += f"   주말: {hours.get('weekend', '정보 없음')}\n"
        
        if detail_level == "medium":
            return result
        
        # 전체 상세 정보
        features = store.get("features", [])
        if features:
            result += f"✅ 특징: {', '.join(features)}\n"
        
        services = store.get("services", [])
        if services:
            result += f"🛍️ 서비스: {', '.join(services)}\n"
        
        landmarks = store.get("nearby_landmarks", [])
        if landmarks:
            result += f"🗺️ 주변: {', '.join(landmarks)}\n"
        
        popular = store.get("popular_products", [])
        if popular:
            result += f"🔥 인기상품: {', '.join(popular[:3])}\n"
        
        return result
    
    def get_all_stores(self) -> List[Dict]:
        """모든 매장 정보를 반환합니다."""
        return self.data["stores"]
    
    def search_by_service(self, service: str) -> List[Dict]:
        """
        특정 서비스를 제공하는 매장을 검색합니다.
        
        Args:
            service: 서비스명 (예: "피부 진단", "면세")
            
        Returns:
            매장 정보 리스트
        """
        service_lower = service.lower()
        results = []
        
        for store in self.data["stores"]:
            services = store.get("services", [])
            if any(service_lower in s.lower() for s in services):
                results.append(store)
        
        return results
    
    def get_brand_info(self, brand_type: str = "all") -> List[str]:
        """
        브랜드 정보를 반환합니다.
        
        Args:
            brand_type: "korean", "international", "all"
            
        Returns:
            브랜드 리스트
        """
        brands = self.data.get("brands", {})
        
        if brand_type == "korean":
            return brands.get("korean", [])
        elif brand_type == "international":
            return brands.get("international", [])
        else:
            return brands.get("korean", []) + brands.get("international", [])
    
    def get_categories(self) -> Dict[str, List[str]]:
        """제품 카테고리 정보를 반환합니다."""
        products = self.data.get("products", {})
        return products.get("by_category", {})
    
    def get_products_by_category(self, category: str) -> List[Dict]:
        """카테고리별 제품 조회"""
        products = self.data.get("products", {})
        by_category = products.get("by_category", {})
        return by_category.get(category, [])
    
    def get_all_products(self) -> List[Dict]:
        """모든 제품 조회"""
        products = self.data.get("products", {})
        return products.get("all_products", [])
    
    def search_products(self, keyword: str, limit: int = 5) -> List[Dict]:
        """키워드로 제품 검색"""
        keyword_lower = keyword.lower()
        results = []
        
        for product in self.get_all_products():
            if keyword_lower in product.get("name", "").lower():
                results.append(product)
                if len(results) >= limit:
                    break
        
        return results
    
    def get_popular_products(self, limit: int = 3) -> List[Dict]:
        """인기 제품 조회 (할인율 높은 순)"""
        products = self.get_all_products()
        # 할인율 순으로 정렬
        sorted_products = sorted(
            products, 
            key=lambda p: p.get("discount_rate", 0), 
            reverse=True
        )
        return sorted_products[:limit]
    
    def get_main_store_image(self) -> Optional[str]:
        """메인 매장 이미지 URL 반환"""
        store = self.data.get("store", {})
        images = store.get("store_images", [])
        return images[0] if images else None

