import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = "your-secret-key-change-in-production"
SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "app.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False

DEEPSEEK_API_KEY = "sk-6536b4f5abcd4f08990152064f7bdab3"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
