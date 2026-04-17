import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = "your-secret-key-change-in-production"
SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "app.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False

DEEPSEEK_API_KEY = "在本地输入API"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# -----------------------------
# Privacy / Compliance demo controls
# -----------------------------
# Data retention period (demo purpose). For real systems, consult your compliance/legal requirements.
DATA_RETENTION_DAYS = 180
# Display which privacy notice version the user accepted.
PRIVACY_CONSENT_VERSION = "v1_2026_04"

# Conservative demo cap for annualised APR display (avoid unrealistic demo products).
HK_MAX_ALLOWED_ANNUAL_APR = 60.0
