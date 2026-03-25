from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Gemini

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # App
    app_env: str = "development"
    max_upload_size_mb: int = 20

    # Storage
    upload_dir: str = "uploads"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()
