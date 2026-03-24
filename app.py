"""
Personalized Bio-Chef — Flask Web Application
Run: python app.py
"""
import json
import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

from src.usda_api import USDAClient
from src.edamam_api import EdamamClient
from src.meal_planner import MealPlanner, SENSITIVITY_RULES
from src.grocery_list import generate_grocery_list, flatten_grocery_list
from src.demo_recipes import DEMO_RECIPES
from config import EDAMAM_APP_ID, EDAMAM_APP_KEY

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

usda = USDAClient()
edamam = EdamamClient()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/sensitivities", methods=["GET"])
def get_sensitivities():
    result = {}
    for key, rule in SENSITIVITY_RULES.items():
        result[key] = {
            "label": key.replace("_", " ").title(),
            "note": rule.get("note", ""),
        }
    return jsonify(result)


@app.route("/api/usda/search", methods=["POST"])
def usda_search():
    data = request.get_json(force=True)
    query = data.get("query", "")
    if not query:
        return jsonify({"error": "query is required"}), 400
    try:
        foods = usda.search_foods(query, page_size=data.get("limit", 10))
        results = [USDAClient.extract_nutrients(f) for f in foods]
        return jsonify({"foods": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate-plan", methods=["POST"])
def generate_plan():
    data = request.get_json(force=True)
    allergies = data.get("allergies", [])
    calories = data.get("calories", 2000)
    macro_split = data.get("macro_split", {"protein": 0.30, "fat": 0.25, "carbs": 0.45})
    sensitivities = data.get("sensitivities", [])
    query = data.get("query", "healthy meal")

    try:
        demo_mode = not (EDAMAM_APP_ID and EDAMAM_APP_KEY)
        all_recipes = []

        if demo_mode:
            all_recipes = list(DEMO_RECIPES)
        else:
            search_queries = [query]
            if "breakfast" not in query.lower():
                search_queries.append("healthy breakfast")
            if "lunch" not in query.lower():
                search_queries.append("healthy lunch")
            if "dinner" not in query.lower():
                search_queries.append("healthy dinner")

            seen_labels = set()
            for q in search_queries:
                recipes = edamam.search_recipes(
                    query=q,
                    allergies=allergies,
                    calorie_range=(150, calories // 3 + 200),
                    max_results=20,
                )
                for r in recipes:
                    if r["label"] not in seen_labels:
                        seen_labels.add(r["label"])
                        all_recipes.append(r)

        if not all_recipes:
            return jsonify({"error": "No recipes found. Check your API keys in config.py or .env"}), 404

        planner = MealPlanner(
            calorie_target=calories,
            macro_split=macro_split,
            allergies=allergies,
            sensitivities=sensitivities,
        )

        plan_df = planner.generate_plan(all_recipes)
        metrics = MealPlanner.evaluate_plan(plan_df, calories)
        grocery_grouped = generate_grocery_list(plan_df, all_recipes)
        grocery_flat = flatten_grocery_list(grocery_grouped)
        sensitivity_notes = planner.get_sensitivity_notes()

        plan_by_day = {}
        for day in range(1, 8):
            day_meals = plan_df[plan_df["day"] == day]
            plan_by_day[str(day)] = day_meals.to_dict(orient="records")

        return jsonify({
            "plan": plan_by_day,
            "metrics": metrics,
            "grocery_list": grocery_flat,
            "grocery_grouped": grocery_grouped,
            "sensitivity_notes": sensitivity_notes,
            "adjusted_macros": planner.macro_split,
            "demo_mode": demo_mode,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/nutrition-lookup", methods=["POST"])
def nutrition_lookup():
    data = request.get_json(force=True)
    query = data.get("query", "")
    if not query:
        return jsonify({"error": "query is required"}), 400
    try:
        foods = usda.search_foods(query, page_size=25)
        results = []
        for f in foods[:10]:
            info = USDAClient.extract_nutrients(f)
            info["fdc_id"] = f.get("fdcId")
            results.append(info)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    print("=" * 50)
    print("  Personalized Bio-Chef")
    print(f"  Open http://127.0.0.1:{port} in your browser")
    print("=" * 50)
    app.run(debug=True, port=port)
