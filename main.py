"""
Personalized Bio-Chef — Nutrition-Aware Meal Planning Agent
CLI Usage: python main.py --allergies peanuts "tree nuts" --calories 2000
Web Usage: python app.py
"""

import argparse
import json
from src.usda_api import USDAClient
from src.edamam_api import EdamamClient
from src.meal_planner import MealPlanner, SENSITIVITY_RULES
from src.grocery_list import generate_grocery_list, flatten_grocery_list
from src.demo_recipes import DEMO_RECIPES
from config import EDAMAM_APP_ID, EDAMAM_APP_KEY


def parse_args():
    parser = argparse.ArgumentParser(description="Personalized Bio-Chef")
    parser.add_argument("--allergies", nargs="*", default=[], help="Allergens to avoid (e.g., peanuts dairy gluten)")
    parser.add_argument("--sensitivities", nargs="*", default=[],
                        help=f"Genetic sensitivities: {', '.join(SENSITIVITY_RULES.keys())}")
    parser.add_argument("--calories", type=int, default=2000, help="Daily calorie target")
    parser.add_argument("--protein", type=float, default=0.30, help="Protein ratio (0-1)")
    parser.add_argument("--fat", type=float, default=0.25, help="Fat ratio (0-1)")
    parser.add_argument("--carbs", type=float, default=0.45, help="Carbs ratio (0-1)")
    parser.add_argument("--query", type=str, default="healthy meal", help="Recipe search query")
    parser.add_argument("--output", type=str, default=None, help="Save plan to JSON file")
    return parser.parse_args()


def main():
    args = parse_args()
    macro_split = {"protein": args.protein, "fat": args.fat, "carbs": args.carbs}

    print(f"[Bio-Chef] Calorie target: {args.calories} kcal/day")
    print(f"[Bio-Chef] Allergies: {args.allergies or 'None'}")
    print(f"[Bio-Chef] Sensitivities: {args.sensitivities or 'None'}")
    print(f"[Bio-Chef] Macro split: P={args.protein:.0%} F={args.fat:.0%} C={args.carbs:.0%}")
    print()

    demo_mode = not (EDAMAM_APP_ID and EDAMAM_APP_KEY)
    if demo_mode:
        print("[Bio-Chef] No Edamam API keys — using demo recipes")
        recipes = list(DEMO_RECIPES)
    else:
        edamam = EdamamClient()
        print("[Bio-Chef] Searching recipes...")
        recipes = edamam.search_recipes(
            query=args.query,
            allergies=args.allergies,
            calorie_range=(200, args.calories // 3 + 100),
            max_results=50,
        )
    print(f"[Bio-Chef] Found {len(recipes)} recipes")

    if not recipes:
        print("[Bio-Chef] No recipes found. Check API keys in config.py or .env")
        return

    planner = MealPlanner(
        calorie_target=args.calories,
        macro_split=macro_split,
        allergies=args.allergies,
        sensitivities=args.sensitivities,
    )

    for note in planner.get_sensitivity_notes():
        print(f"[Bio-Chef] {note}")

    plan_df = planner.generate_plan(recipes)

    print("\n===== 7-Day Meal Plan =====\n")
    for day in range(1, 8):
        day_meals = plan_df[plan_df["day"] == day]
        print(f"--- Day {day} ---")
        for _, row in day_meals.iterrows():
            print(f"  {row['meal']}: {row['recipe']} ({row['calories']} kcal)")
        daily_cal = day_meals["calories"].sum()
        print(f"  Total: {daily_cal} kcal\n")

    metrics = MealPlanner.evaluate_plan(plan_df, args.calories)
    print(f"[Metrics] Calorie MAE: {metrics['calorie_mae']} kcal | "
          f"Diversity: {metrics['unique_recipes']}/{metrics['total_recipes']} unique recipes")

    grocery = flatten_grocery_list(generate_grocery_list(plan_df, recipes))
    print(f"\n===== Grocery List ({len(grocery)} items) =====\n")
    for item in grocery:
        print(f"  - {item}")

    if args.output:
        output = {
            "plan": plan_df.to_dict(orient="records"),
            "metrics": metrics,
            "grocery_list": grocery,
        }
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\n[Bio-Chef] Plan saved to {args.output}")


if __name__ == "__main__":
    main()
