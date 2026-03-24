import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

USDA_API_KEY = os.getenv("USDA_API_KEY", "DEMO_KEY")
USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

EDAMAM_APP_ID = os.getenv("EDAMAM_APP_ID", "")
EDAMAM_APP_KEY = os.getenv("EDAMAM_APP_KEY", "")
EDAMAM_BASE_URL = "https://api.edamam.com/api/recipes/v2"

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "cache.db")

DEFAULT_CALORIE_TARGET = 2000
DEFAULT_MACRO_SPLIT = {"protein": 0.30, "fat": 0.25, "carbs": 0.45}
MEALS_PER_DAY = 3
PLAN_DAYS = 7
