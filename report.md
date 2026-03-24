# Personalized Bio-Chef: A Nutrition-Aware Meal Planning Agent with Biological Constraint Satisfaction

**Authors:** Yunfei Zhou

**Course:** CS6220 — Data Mining Techniques

---

## 1. Introduction

### 1.1 Background

Diet-related chronic diseases, including type 2 diabetes, cardiovascular disease, and obesity, remain among the leading causes of morbidity worldwide [1]. While general dietary guidelines exist, they fail to address individual biological variability. Genetic conditions such as phenylketonuria (PKU), glucose-6-phosphate dehydrogenase (G6PD) deficiency, and celiac disease impose strict dietary constraints that generic meal planners cannot accommodate [2]. Furthermore, food allergies affect approximately 8% of children and 10% of adults in the United States [3], making personalized nutrition planning a critical public health need.

Existing commercial meal planning applications (e.g., MyFitnessPal, Eat This Much) offer calorie tracking and basic dietary preferences but lack integration with authoritative nutritional databases and fail to model genetic or biological sensitivities at the algorithmic level. There is a gap between clinical nutrition knowledge and accessible consumer tools.

### 1.2 Solution Overview

Bio-Chef is an AI-powered nutrition agent that generates personalized 7-day meal plans by cross-referencing real-time recipe data with the user's caloric targets, allergen restrictions, and self-reported genetic sensitivities. The system mines the USDA FoodData Central database for authoritative nutritional information and the Edamam Recipe Search API for a diverse recipe pool. A constraint-satisfaction algorithm with diversity-aware scoring produces meal plans that balance nutritional accuracy with variety. The application additionally generates an automated grocery list aggregated from all planned meals.

---

## 2. Methods

### 2.1 System Architecture

Bio-Chef follows a three-tier architecture:

1. **Data Layer** — Two external APIs (USDA FoodData Central, Edamam Recipe Search) provide nutritional data and recipe content.
2. **Intelligence Layer** — A Python-based planning engine performs sensitivity-aware macro adjustment, constraint-based recipe filtering, and greedy optimization with stochastic diversification.
3. **Presentation Layer** — A Flask web application serves a responsive single-page interface for user interaction.

### 2.2 External API Integration

**USDA FoodData Central API.** The USDA API provides authoritative per-100g nutritional data for over 300,000 food items across multiple data types: Foundation, SR Legacy, Survey (FNDDS), and Branded [4]. Our client queries the `/foods/search` endpoint and applies a ranking heuristic that prioritizes Foundation and SR Legacy data over Branded products, addressing the issue of irrelevant commercial products appearing in search results (e.g., branded candy items appearing for a query like "egg"). Key nutrients extracted include energy (kcal), protein, fat, carbohydrates, fiber, calcium, iron, sodium, vitamin A, and vitamin C, mapped via USDA nutrient IDs.

**Edamam Recipe Search API.** The Edamam API provides structured recipe data including per-serving macronutrient breakdowns, ingredient lists, health labels (e.g., "gluten-free", "dairy-free"), and image URLs [5]. Our client translates user-specified allergies into Edamam's health label filter parameters. To maximize recipe diversity, the system issues multiple search queries (user query plus "healthy breakfast", "healthy lunch", "healthy dinner") and deduplicates results by recipe label.

### 2.3 Biological Sensitivity Modeling

A key contribution of Bio-Chef is its sensitivity rule engine, which encodes dietary constraints for eight genetic and biological conditions:

| Condition | Constraint Type | Mechanism |
|---|---|---|
| Lactose Intolerance | Label filter | Requires "dairy-free" health label |
| Celiac Disease | Label filter | Requires "gluten-free" health label |
| G6PD Deficiency | Keyword filter | Excludes recipes containing fava beans, broad beans, soy, legumes |
| Phenylketonuria (PKU) | Macro adjustment | Caps protein ratio at 10%, redistributes to fat/carbs proportionally |
| Fructose Malabsorption | Keyword filter | Excludes high-fructose ingredients (honey, agave, apple, pear, mango) |
| Histamine Intolerance | Keyword filter | Excludes fermented, aged, and smoked foods |
| Caffeine Sensitivity | Keyword filter | Excludes coffee, espresso, matcha, energy drinks |
| Type 2 Diabetes | Macro adjustment | Caps carbohydrate ratio at 35%, redistributes to protein/fat proportionally |

Macro adjustments use proportional redistribution: when a macronutrient is capped, the remaining caloric budget is distributed among the other macronutrients in proportion to their original ratios, ensuring the total always sums to 100%.

### 2.4 Meal Planning Algorithm

The planning algorithm is a greedy constraint-satisfaction procedure with stochastic top-k selection:

**Input:** Recipe pool *R*, calorie target *C*, macro split *M*, sensitivity rules *S*.

**Step 1 — Sensitivity Filtering.** Each recipe *r ∈ R* is evaluated against all active sensitivity rules. For keyword-based rules, the recipe label and full ingredient list are scanned for prohibited terms. For label-based rules, the recipe's health labels are checked for the required "X-free" designation. Recipes failing any rule are removed from the candidate pool.

**Step 2 — Per-Meal Target Computation.** The daily calorie target is divided equally among 3 meals. Macro targets in grams are derived using standard conversion factors: 4 kcal/g for protein and carbohydrates, 9 kcal/g for fat.

**Step 3 — Greedy Selection with Diversification.** For each of the 21 meal slots (7 days × 3 meals), all candidate recipes are scored. The scoring function is:

$$\text{score}(r) = \sum_{k \in \{cal, P, F, C\}} \frac{|r_k - t_k|}{\max(t_k, 1)} + \lambda \cdot \mathbb{1}[r \in \text{used}] + \epsilon$$

where *t_k* is the per-meal target for nutrient *k*, *λ* = 5.0 is the diversity penalty for previously used recipes, and *ε* ~ Uniform(0, 0.3) introduces controlled randomness. The top 5 scoring recipes are identified, and one is selected uniformly at random, balancing optimization quality with variety.

**Step 4 — Evaluation.** Plan quality is assessed via Calorie Mean Absolute Error (MAE) between daily totals and the target, and a diversity index (unique recipes / total slots).

### 2.5 Grocery List Generation

Ingredients from all unique recipes in the plan are aggregated, cleaned (whitespace normalization), and deduplicated via case-insensitive comparison. The output is a sorted flat list suitable for shopping.

---

## 3. Dataset and Inputs

### 3.1 Data Sources

| Source | Type | Access | Content |
|---|---|---|---|
| USDA FoodData Central [4] | REST API | Free (DEMO_KEY or registered key) | 300,000+ food items with detailed nutrient profiles |
| Edamam Recipe Search API [5] | REST API | Free tier (10,000 requests/month) | Millions of recipes with structured nutrition, health labels, and ingredients |

### 3.2 User Inputs

The application accepts the following user inputs through its web interface:

- **Daily Calorie Target:** Adjustable via slider (1,200–4,000 kcal)
- **Allergies:** Multi-select from 8 common allergens (gluten, dairy, egg, soy, peanuts, tree nuts, fish, shellfish)
- **Genetic Sensitivities:** Multi-select from 8 biological conditions
- **Macronutrient Split:** Adjustable protein/fat/carbs ratios via individual sliders
- **Recipe Preference:** Free-text query for cuisine or dietary style (e.g., "Mediterranean", "Asian", "Low-carb")

### 3.3 Data Processing Pipeline

1. User inputs are sent as JSON to the Flask backend.
2. The Edamam API is queried with allergy filters and calorie range constraints applied server-side.
3. Raw recipe JSON is parsed to extract per-serving nutritional values (total nutrients divided by yield/servings).
4. The sensitivity filter scans recipe labels and ingredient text against prohibited keyword and label rules.
5. The planning algorithm scores and selects recipes for 21 meal slots.
6. Pandas DataFrames are used for plan aggregation, daily totals, and metric computation.
7. For USDA lookups, raw search results are re-ranked to prioritize authoritative data types over branded products.

---

## 4. Results

### 4.1 Application Overview

Bio-Chef provides a fully functional web interface accessible at `http://127.0.0.1:5001`. The main interface presents a user profile form where calorie targets, allergies, sensitivities, and macro splits are configured. Upon clicking "Generate 7-Day Meal Plan", the system queries external APIs, runs the planning algorithm, and renders results within seconds.

### 4.2 Key Functionality Demonstration

**Meal Plan Generation.** The system produces a 7-day, 3-meals-per-day plan. Each meal displays the recipe name (linked to the source), a thumbnail image, and per-meal macronutrient breakdown (calories, protein, fat, carbs). Daily calorie totals are shown per day.

**Sensitivity-Aware Adjustments.** When a user selects "Diabetes Type 2", the system automatically reduces the carbohydrate ratio from the default 45% to a maximum of 35% and proportionally increases protein and fat. A visible "Dietary Adjustments" banner explains the applied constraints.

**Plan Quality Metrics.** The metrics panel displays average daily calories, macronutrient totals, Calorie MAE, and a diversity index. In testing with a 2,000 kcal target and no restrictions, typical Calorie MAE values ranged from 200–500 kcal with diversity indices of 0.7–1.0 (15–21 unique recipes out of 21 slots).

**USDA Nutrition Lookup.** The integrated USDA tab allows users to search any food item and view a detailed nutrition table. Results are ranked with authoritative USDA data (Foundation, SR Legacy) displayed before branded products, with category, serving size, and data type metadata included.

**Automated Grocery List.** The grocery tab displays a deduplicated, sorted list of all ingredients needed for the 7-day plan, ready for shopping.

### 4.3 Demo Mode

When Edamam API keys are not configured, the system operates in demo mode using a built-in pool of 21 curated recipes with accurate nutritional data, enabling full functionality testing without API credentials.

---

## 5. Discussion

### 5.1 Comparison with Existing Solutions

| Feature | MyFitnessPal | Eat This Much | Bio-Chef |
|---|---|---|---|
| Calorie tracking | Yes | Yes | Yes |
| Allergy filtering | Limited | Yes | Yes (8 allergens) |
| Genetic sensitivity modeling | No | No | **Yes (8 conditions)** |
| USDA database integration | No | No | **Yes** |
| Macro auto-adjustment for conditions | No | No | **Yes** |
| Open-source | No | No | **Yes** |
| Free | Freemium | Freemium | **Fully free** |

Bio-Chef's primary differentiation is its biological sensitivity engine, which goes beyond simple allergen filtering to model conditions like PKU and diabetes with automatic macronutrient ratio adjustment — a feature absent from mainstream consumer applications.

### 5.2 Challenges

1. **API Rate Limits.** The USDA DEMO_KEY allows only 30 requests/hour. The Edamam free tier caps at 10,000 requests/month. For production use, caching and rate-limiting middleware would be necessary.
2. **Recipe Diversity vs. Nutritional Fit.** With a small recipe pool (e.g., 20–60 recipes from API results), achieving both high diversity and low Calorie MAE across 21 slots is inherently a trade-off. The stochastic top-k selection balances these competing objectives.
3. **Sensitivity Keyword Matching.** Keyword-based filtering (e.g., scanning for "fava bean" in ingredient text) can produce false positives or miss relevant items due to variation in ingredient naming conventions.

### 5.3 Lessons Learned

- Integrating multiple external APIs requires careful error handling and graceful degradation (demo mode fallback).
- USDA search results contain heterogeneous data types; naive display of results misleads users (e.g., branded candy appearing for "egg").
- Greedy algorithms with controlled randomness provide a practical balance between optimality and user experience in meal planning.

### 5.4 Future Improvements

1. **LLM Integration.** Incorporate a large language model (e.g., GPT-4) to provide natural-language dietary coaching and explain why specific recipes were selected or excluded.
2. **Caching Layer.** Add SQLite or Redis caching for API responses to reduce latency and API usage.
3. **User Accounts.** Persistent user profiles to save preferences, plan history, and track adherence over time.
4. **Nutrient Micromanagement.** Extend beyond macros to optimize for micronutrients (iron, calcium, vitamin D) based on user demographics.
5. **Meal Prep Optimization.** Suggest recipes that share common ingredients to minimize grocery waste and cooking time.

---

## 6. AI Prompts Used

All development was assisted by Claude (Anthropic) through the Cursor IDE. Below is a comprehensive log of prompts used:

### Coding Prompts

1. **Initial project scaffolding:** "现在开始构建符合要求的project (已经完成的部分检查即可）。前端也要写好。告诉我如何打开（并test）" — Used to generate the Flask web application, frontend HTML/CSS/JS, and integrate all backend modules.

2. **Sensitivity engine design:** Part of the initial scaffolding prompt — Claude generated the `SENSITIVITY_RULES` dictionary and the macro adjustment algorithm based on the project requirements for "Genetic Sensitivities (Self-reported)".

3. **Demo recipe pool:** Generated as part of the fallback mechanism when Edamam API keys are not configured.

### Debugging Prompts

4. **Port conflict resolution:** "怎么关掉" — Resolved macOS AirPlay Receiver occupying port 5000; changed default port to 5001.

5. **Edamam 401 error:** "Error: 401 Client Error for url: https://api.edamam.com/api/recipes/v2..." — Diagnosed that the new "Recipe Search and Meal Planner API" requires the `Edamam-Account-User` HTTP header.

6. **USDA search quality:** "我查询usda 输入egg 为什么出来5个？usda_api 正确连上了吗？这个是不是还需要优化？" — Led to implementing the `_rank_foods` method to prioritize Foundation/SR Legacy data over Branded products.

### Explanation Prompts

7. **Code walkthrough:** "解释一下这个project的代码（前端不用解释）主要是各种api的代码" — Used to verify understanding of the codebase architecture and API integration logic.

8. **USDA API key inquiry:** "为什么usda 不用key? 我根本没改key就能直接用？" — Clarified the DEMO_KEY mechanism.

9. **Edamam API key setup:** "我去这个网站注册了，然后选择了developer的api...然后我去了dashboard没找到什么key之类的东西？" — Guided through the Edamam application creation process.

---

## 7. References

[1] World Health Organization. "Diet, Nutrition and the Prevention of Chronic Diseases." WHO Technical Report Series 916, 2003.

[2] Camp, K. M., and Lloyd-Puryear, M. A. "Personalizing Medical Nutrition Therapy for Inborn Errors of Metabolism." *Molecular Genetics and Metabolism*, vol. 137, no. 1-2, pp. 213–217, 2022.

[3] Gupta, R. S., et al. "Prevalence and Severity of Food Allergies Among US Adults." *JAMA Network Open*, vol. 2, no. 1, e185630, 2019.

[4] U.S. Department of Agriculture, Agricultural Research Service. "FoodData Central." https://fdc.nal.usda.gov/, 2024.

[5] Edamam LLC. "Edamam Recipe Search API Documentation." https://developer.edamam.com/, 2024.

[6] Harris, J. A., and Benedict, F. G. "A Biometric Study of Human Basal Metabolism." *Proceedings of the National Academy of Sciences*, vol. 4, no. 12, pp. 370–373, 1918.

[7] McKinney, W. "Data Structures for Statistical Computing in Python." *Proceedings of the 9th Python in Science Conference*, pp. 56–61, 2010.

---

## Appendix

### A. Code Repository

**GitHub:** https://github.com/Nasdaq101/bio-chef

### B. Installation and Setup

```bash
# Clone the repository
git clone https://github.com/Nasdaq101/bio-chef.git
cd bio-chef

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys (optional — demo mode works without keys)
cp .env.example .env
# Edit .env with your Edamam APP_ID and APP_KEY

# Run the web application
python3 app.py
# Open http://127.0.0.1:5001 in your browser

# Alternative: CLI mode
python3 main.py --allergies peanuts dairy --sensitivities diabetes_type2 --calories 1800
```

### C. Project File Structure

```
bio-chef/
├── app.py                  # Flask web server (4 API endpoints)
├── main.py                 # CLI entry point
├── config.py               # Centralized configuration
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── templates/
│   └── index.html          # Frontend HTML
├── static/
│   ├── style.css           # Responsive CSS
│   └── app.js              # Frontend JavaScript
└── src/
    ├── usda_api.py          # USDA FoodData Central client
    ├── edamam_api.py        # Edamam Recipe Search client
    ├── meal_planner.py      # Constraint-satisfaction planning engine
    ├── grocery_list.py      # Grocery list aggregator
    └── demo_recipes.py      # Fallback recipe pool (21 recipes)
```

### D. Dependencies

| Package | Version | Purpose |
|---|---|---|
| Flask | ≥ 3.0.0 | Web framework |
| flask-cors | ≥ 4.0.0 | Cross-origin resource sharing |
| requests | ≥ 2.31.0 | HTTP client for API calls |
| pandas | ≥ 2.1.0 | Data manipulation and aggregation |
| numpy | ≥ 1.24.0 | Numerical computation (MAE, statistics) |
| python-dotenv | ≥ 1.0.0 | Environment variable loading |

### E. Statement of Contributions

Solo project — all work completed by Yunfei Zhou.
