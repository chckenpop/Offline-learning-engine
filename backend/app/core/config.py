import os
from dotenv import load_dotenv

# Load .env from the backend directory
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

SECRET_KEY: str = os.getenv("SECRET_KEY", "offline-learning-dev-secret-change-in-prod")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24h

# Database — stored in backend/data/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
PROJECT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))

DATABASE_PATH: str = os.getenv(
    "DATABASE_PATH",
    os.path.join(BACKEND_DIR, "data", "app.db"),
)

# Content directories (shared with engine/)
CONTENT_DIR: str = os.path.join(PROJECT_DIR, "content")
LESSONS_DIR: str = os.path.join(CONTENT_DIR, "lessons")
CONCEPTS_DIR: str = os.path.join(CONTENT_DIR, "concepts")
PROGRESS_DB_PATH: str = os.path.join(PROJECT_DIR, "database", "progress.db")

# Supabase Config
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://njqlzvelsatdwzwynyek.supabase.co")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "sb_publishable_NOFcz2mruM_oYS8NaKWlIg_lrXZqXEM")
