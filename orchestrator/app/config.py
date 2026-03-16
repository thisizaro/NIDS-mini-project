import os

CICFLOWMETER_URL = os.getenv("CICFLOWMETER_URL", "http://localhost:8010")
PREPROCESSOR_URL = os.getenv("PREPROCESSOR_URL", "http://localhost:8001")
DECISION_ENGINE_URL = os.getenv("DECISION_ENGINE_URL", "http://localhost:8002")
MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://localhost:8003")

REQUEST_TIMEOUT = 300.0  # 5 minutes for large PCAPs

# # Increased timeout for large PCAPs
