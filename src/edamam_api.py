import requests
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import EDAMAM_APP_ID, EDAMAM_APP_KEY, EDAMAM_BASE_URL


HEALTH_LABEL_MAP = {
    "gluten": "gluten-free",
    "dairy": "dairy-free",
    "egg": "egg-free",
    "soy": "soy-free",
    "tree nuts": "tree-nut-free",
    "peanuts": "peanut-free",
    "fish": "fish-free",
    "shellfish": "shellfish-free",
}


class EdamamClient:
    def __init__(self, app_id: str = EDAMAM_APP_ID, app_key: str = EDAMAM_APP_KEY):
        self.app_id = app_id
        self.app_key = app_key
        self.base_url = EDAMAM_BASE_URL

    def search_recipes(
        self,
        query: str,
        allergies: list[str] | None = None,
        calorie_range: tuple[int, int] | None = None,
        meal_type: str | None = None,
        max_results: int = 10,
    ) -> list[dict]:
        params = {
            "type": "public",
            "q": query,
            "app_id": self.app_id,
            "app_key": self.app_key,
        }
        if allergies:
            labels = [HEALTH_LABEL_MAP[a] for a in allergies if a in HEALTH_LABEL_MAP]
            for label in labels:
                params.setdefault("health", [])
                if isinstance(params["health"], list):
                    params["health"].append(label)
        if calorie_range:
            params["calories"] = f"{calorie_range[0]}-{calorie_range[1]}"
        if meal_type:
            params["mealType"] = meal_type

        headers = {"Edamam-Account-User": self.app_id}
        resp = requests.get(self.base_url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])[:max_results]
        return [self._parse_recipe(h["recipe"]) for h in hits]

    @staticmethod
    def _parse_recipe(recipe: dict) -> dict:
        servings = recipe.get("yield", 1) or 1
        total_nutrients = recipe.get("totalNutrients", {})
        return {
            "label": recipe.get("label", ""),
            "url": recipe.get("url", ""),
            "image": recipe.get("image", ""),
            "servings": servings,
            "ingredients": [i.get("text", "") for i in recipe.get("ingredients", [])],
            "health_labels": recipe.get("healthLabels", []),
            "calories": total_nutrients.get("ENERC_KCAL", {}).get("quantity", 0) / servings,
            "protein": total_nutrients.get("PROCNT", {}).get("quantity", 0) / servings,
            "fat": total_nutrients.get("FAT", {}).get("quantity", 0) / servings,
            "carbs": total_nutrients.get("CHOCDF", {}).get("quantity", 0) / servings,
        }
