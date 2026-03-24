import random
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DEFAULT_CALORIE_TARGET, DEFAULT_MACRO_SPLIT, MEALS_PER_DAY, PLAN_DAYS

SENSITIVITY_RULES = {
    "lactose_intolerance": {
        "avoid_labels": ["dairy"],
        "health_filters": ["dairy-free"],
        "note": "Avoid dairy products — use lactose-free alternatives",
    },
    "celiac_disease": {
        "avoid_labels": ["gluten", "wheat"],
        "health_filters": ["gluten-free"],
        "note": "Strict gluten-free diet required",
    },
    "g6pd_deficiency": {
        "avoid_keywords": ["fava bean", "broad bean", "soy", "legume"],
        "note": "Avoid fava beans, certain legumes, and soy products",
    },
    "phenylketonuria": {
        "max_protein_ratio": 0.10,
        "avoid_keywords": ["aspartame"],
        "note": "Strict low-phenylalanine diet — limit protein intake",
    },
    "fructose_malabsorption": {
        "avoid_keywords": ["honey", "agave", "apple", "pear", "mango", "watermelon", "high-fructose"],
        "note": "Avoid high-fructose fruits and sweeteners",
    },
    "histamine_intolerance": {
        "avoid_keywords": ["aged cheese", "fermented", "smoked", "canned fish", "wine", "vinegar", "sauerkraut"],
        "note": "Avoid fermented, aged, and histamine-rich foods",
    },
    "caffeine_sensitivity": {
        "avoid_keywords": ["coffee", "espresso", "matcha", "caffeine", "energy drink"],
        "note": "Limit or avoid caffeine-containing foods and drinks",
    },
    "diabetes_type2": {
        "max_carb_ratio": 0.35,
        "prefer_low_gi": True,
        "note": "Low glycemic index diet — limit carbohydrate intake",
    },
}


class MealPlanner:
    def __init__(
        self,
        calorie_target: int = DEFAULT_CALORIE_TARGET,
        macro_split: dict | None = None,
        allergies: list[str] | None = None,
        sensitivities: list[str] | None = None,
    ):
        self.calorie_target = calorie_target
        self.macro_split = dict(macro_split or DEFAULT_MACRO_SPLIT)
        self.allergies = allergies or []
        self.sensitivities = sensitivities or []
        self._apply_sensitivity_adjustments()
        self.meal_targets = self._compute_meal_targets()

    def _apply_sensitivity_adjustments(self):
        # i add macro target adjustments, important for sensitivity rules
        for s in self.sensitivities:
            rule = SENSITIVITY_RULES.get(s, {})
            if "max_protein_ratio" in rule:
                self.macro_split["protein"] = min(self.macro_split["protein"], rule["max_protein_ratio"])
                remainder = 1.0 - self.macro_split["protein"]
                fat_carb_sum = self.macro_split["fat"] + self.macro_split["carbs"]
                if fat_carb_sum > 0:
                    self.macro_split["fat"] = remainder * (self.macro_split["fat"] / fat_carb_sum)
                    self.macro_split["carbs"] = remainder * (self.macro_split["carbs"] / fat_carb_sum)
            if "max_carb_ratio" in rule:
                self.macro_split["carbs"] = min(self.macro_split["carbs"], rule["max_carb_ratio"])
                remainder = 1.0 - self.macro_split["carbs"]
                pf_sum = self.macro_split["protein"] + self.macro_split["fat"]
                if pf_sum > 0:
                    self.macro_split["protein"] = remainder * (self.macro_split["protein"] / pf_sum)
                    self.macro_split["fat"] = remainder * (self.macro_split["fat"] / pf_sum)

    def _compute_meal_targets(self) -> dict:
        cal_per_meal = self.calorie_target / MEALS_PER_DAY
        return {
            "calories": cal_per_meal,
            "protein": cal_per_meal * self.macro_split["protein"] / 4,
            "fat": cal_per_meal * self.macro_split["fat"] / 9,
            "carbs": cal_per_meal * self.macro_split["carbs"] / 4,
        }

    def _recipe_passes_sensitivity_filter(self, recipe: dict) -> bool:
        label_lower = recipe.get("label", "").lower()
        ingredients_text = " ".join(recipe.get("ingredients", [])).lower()
        combined_text = f"{label_lower} {ingredients_text}"

        for s in self.sensitivities:
            rule = SENSITIVITY_RULES.get(s, {})
            for keyword in rule.get("avoid_keywords", []):
                if keyword.lower() in combined_text:
                    return False
            for bad_label in rule.get("avoid_labels", []):
                health_labels = [hl.lower() for hl in recipe.get("health_labels", [])]
                free_label = f"{bad_label}-free"
                if free_label.lower() not in health_labels:
                    return False
        return True

    def score_recipe(self, recipe: dict, used_labels: set, day: int, meal_idx: int) -> float:
        targets = self.meal_targets
        macro_error = sum(
            abs(recipe.get(k, 0) - targets[k]) / max(targets[k], 1)
            for k in ["calories", "protein", "fat", "carbs"]
        )
        diversity_penalty = 5.0 if recipe["label"] in used_labels else 0.0
        randomness = random.uniform(0, 0.3)
        return macro_error + diversity_penalty + randomness

    def generate_plan(self, recipe_pool: list[dict]) -> pd.DataFrame:
        if not recipe_pool:
            raise ValueError("Recipe pool is empty. Fetch recipes first.")

        filtered_pool = [r for r in recipe_pool if self._recipe_passes_sensitivity_filter(r)]
        if not filtered_pool:
            filtered_pool = recipe_pool

        plan_rows = []
        used_labels: set[str] = set()
        meal_types = ["Breakfast", "Lunch", "Dinner"]

        for day in range(1, PLAN_DAYS + 1):
            day_calories = 0
            for meal_idx in range(MEALS_PER_DAY):
                scored = [(r, self.score_recipe(r, used_labels, day, meal_idx)) for r in filtered_pool]
                scored.sort(key=lambda x: x[1])
                top_k = scored[:min(5, len(scored))]
                best = random.choice(top_k)[0]
                used_labels.add(best["label"])
                day_calories += best["calories"]
                plan_rows.append({
                    "day": day,
                    "meal": meal_types[meal_idx % len(meal_types)],
                    "recipe": best["label"],
                    "calories": round(best["calories"]),
                    "protein_g": round(best["protein"], 1),
                    "fat_g": round(best["fat"], 1),
                    "carbs_g": round(best["carbs"], 1),
                    "url": best["url"],
                    "image": best.get("image", ""),
                })

        return pd.DataFrame(plan_rows)

    @staticmethod
    def evaluate_plan(plan_df: pd.DataFrame, calorie_target: int) -> dict:
        daily = plan_df.groupby("day").agg({
            "calories": "sum", "protein_g": "sum", "fat_g": "sum", "carbs_g": "sum"
        })
        cal_mae = np.mean(np.abs(daily["calories"] - calorie_target))
        unique_ratio = plan_df["recipe"].nunique() / len(plan_df)
        return {
            "calorie_mae": round(float(cal_mae), 1),
            "diversity_index": round(float(unique_ratio), 3),
            "total_recipes": int(len(plan_df)),
            "unique_recipes": int(plan_df["recipe"].nunique()),
            "avg_daily_calories": round(float(daily["calories"].mean()), 1),
            "avg_daily_protein": round(float(daily["protein_g"].mean()), 1),
            "avg_daily_fat": round(float(daily["fat_g"].mean()), 1),
            "avg_daily_carbs": round(float(daily["carbs_g"].mean()), 1),
        }

    def get_sensitivity_notes(self) -> list[str]:
        notes = []
        for s in self.sensitivities:
            rule = SENSITIVITY_RULES.get(s, {})
            if "note" in rule:
                notes.append(f"[{s.replace('_', ' ').title()}] {rule['note']}")
        return notes
