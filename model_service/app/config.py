import os

# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# PROJECT_ROOT = os.path.dirname(BASE_DIR)

# MODEL_PATH = os.path.join(PROJECT_ROOT, "trained_models", "cnn_openmax", "best_model.keras")
# OPENMAX_PARAMS_PATH = os.path.join(PROJECT_ROOT, "trained_models", "cnn_openmax", "openmax_params.json")
# SCALER_PATH = os.path.join(PROJECT_ROOT, "trained_models", "preprocessing", "scaler_infogan_kaggle.pkl")
# FEATURE_COLS_PATH = os.path.join(PROJECT_ROOT, "trained_models", "preprocessing", "infogan_kaggle_feature_cols.json")



# Explicit base path for models (Docker-friendly)
MODEL_BASE_PATH = os.getenv("MODEL_BASE_PATH", "/app/trained_models")

MODEL_PATH = os.path.join(MODEL_BASE_PATH, "cnn_openmax", "best_model.keras")
OPENMAX_PARAMS_PATH = os.path.join(MODEL_BASE_PATH, "cnn_openmax", "openmax_params.json")
SCALER_PATH = os.path.join(MODEL_BASE_PATH, "preprocessing", "scaler_infogan_kaggle.pkl")
FEATURE_COLS_PATH = os.path.join(MODEL_BASE_PATH, "preprocessing", "infogan_kaggle_feature_cols.json")



NUM_KNOWN_CLASSES = 6
ALPHA_RANK = 5
DISTANCE_TYPE = "cosine"

CLASS_NAMES = {
    0: "Normal",
    1: "Botnet",
    2: "Brute Force",
    3: "DoS",
    4: "PortScan",
    5: "Web Attack",
    6: "Unknown",
}

IMAGE_SIZE = 11  # 11x11 = 121 pixels
IMAGE_PIXELS = IMAGE_SIZE * IMAGE_SIZE  # 121
