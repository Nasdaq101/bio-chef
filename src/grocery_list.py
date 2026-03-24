import re
from collections import defaultdict


def generate_grocery_list(plan_df, recipe_pool: list[dict]) -> dict[str, list[str]]:
    """Aggregate ingredients from all recipes in the plan, grouped by recipe."""
    recipe_map = {r["label"]: r for r in recipe_pool}
    grocery: dict[str, list[str]] = defaultdict(list)

    for recipe_name in plan_df["recipe"].unique():
        recipe = recipe_map.get(recipe_name, {})
        for ingredient in recipe.get("ingredients", []):
            cleaned = _clean_ingredient(ingredient)
            if cleaned:
                grocery[recipe_name].append(cleaned)

    return dict(grocery)


def flatten_grocery_list(grouped: dict[str, list[str]]) -> list[str]:
    """Return a deduplicated flat list of all ingredients."""
    seen = set()
    flat = []
    for items in grouped.values():
        for item in items:
            normalized = item.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                flat.append(item)
    return sorted(flat)


def _clean_ingredient(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text
