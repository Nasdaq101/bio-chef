import requests
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import USDA_API_KEY, USDA_BASE_URL

PREFERRED_DATA_TYPES = ["Foundation", "SR Legacy", "Survey (FNDDS)"]


class USDAClient:
    def __init__(self, api_key: str = USDA_API_KEY):
        self.api_key = api_key
        self.base_url = USDA_BASE_URL

    def search_foods(self, query: str, page_size: int = 25) -> list[dict]:
        resp = requests.get(
            f"{self.base_url}/foods/search",
            params={
                "api_key": self.api_key,
                "query": query,
                "pageSize": page_size,
            },
            timeout=15,
        )
        resp.raise_for_status()
        foods = resp.json().get("foods", [])
        return self._rank_foods(foods)

    def get_food(self, fdc_id: int) -> dict:
        resp = requests.get(
            f"{self.base_url}/food/{fdc_id}",
            params={"api_key": self.api_key},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    # i add this function to prioritize data type
    @staticmethod
    def _rank_foods(foods: list[dict]) -> list[dict]:
        """Prioritize Foundation/SR Legacy/Survey data over Branded products."""
        def sort_key(f):
            dt = f.get("dataType", "")
            if dt in PREFERRED_DATA_TYPES:
                return (0, f.get("description", ""))
            return (1, f.get("description", ""))
        return sorted(foods, key=sort_key)

    @staticmethod
    def extract_nutrients(food: dict) -> dict:
        nutrient_map = {
            1008: "calories",
            1003: "protein",
            1004: "fat",
            1005: "carbs",
            1079: "fiber",
            1087: "calcium",
            1089: "iron",
            1093: "sodium",
            1104: "vitamin_a",
            1162: "vitamin_c",
        }
        desc = food.get("description", "")
        brand = food.get("brandName") or food.get("brandOwner") or ""
        category = food.get("foodCategory", "")
        data_type = food.get("dataType", "")
        serving_size = food.get("servingSize")
        serving_unit = food.get("servingSizeUnit", "g")

        full_desc = desc
        if brand:
            full_desc = f"{desc} ({brand})"

        result = {
            "description": full_desc,
            "category": category,
            "data_type": data_type,
            "serving_size": f"{serving_size} {serving_unit}" if serving_size else "100 g (standard)",
        }
        for n in food.get("foodNutrients", []):
            nid = n.get("nutrientId") or n.get("nutrient", {}).get("id")
            if nid in nutrient_map:
                result[nutrient_map[nid]] = n.get("value") or n.get("amount", 0)
        return result
