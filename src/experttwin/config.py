from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ExpertTwin"
    data_dir: Path = Path("./data")
    max_upload_mb: int = Field(default=25, ge=1, le=200)

    extractor_provider: str = "heuristic"
    chat_provider: str = "local"
    transcription_provider: str = "local"
    war_room_provider: str = "disabled"
    war_room_prompt_budget: int = Field(default=24000, ge=8000, le=60000)

    azure_openai_endpoint: str | None = None
    azure_openai_chat_deployment: str | None = None
    azure_openai_api_version: str = "2025-04-01-preview"
    azure_openai_api_key: str | None = None

    azure_speech_key: str | None = None
    azure_speech_region: str | None = None
    azure_speech_language: str = "en-US"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "experttwin.db"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    def prepare(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
