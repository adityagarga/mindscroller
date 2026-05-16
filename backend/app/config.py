from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent.parent
MEDIA_DIR = BACKEND_DIR / "media"
DB_PATH = BACKEND_DIR / "mindscroller.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    fal_key: str = ""
    gradium_api_key: str = ""

    openai_model: str = "gpt-4o-2024-08-06"
    fal_image_model: str = "fal-ai/flux/schnell"
    gradium_base_url: str = "https://api.gradium.ai"
    gradium_voice_id: str = "RhI-l8fGE2DtXgXV"  # Wren — professional male voice (catalog)
    gradium_model_name: str = "default"


settings = Settings()
