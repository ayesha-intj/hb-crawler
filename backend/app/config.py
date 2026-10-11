from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from app import __version__

BACKEND_DIR = Path(__file__).resolve().parent.parent  # .../hb-crawler/backend
DATA_DIR = BACKEND_DIR / "data"
DEFAULT_DATABASE_URL = f"sqlite:///{(DATA_DIR / 'hb_crawler.db').as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )
    contact_email: str = "ayesha24442@gmail.com"
    database_url: str = DEFAULT_DATABASE_URL
    cors_origins: str = "http://localhost:3000"

    # The site's robots.txt asks crawlers for 10 s.
    crawl_delay_seconds: float = Field(default=10.0, ge=5.0)
    max_listing_pages: int = Field(default=3, ge=1, le=50)
    max_new_jobs: int = Field(default=50, ge=1, le=1000)
    job_retention_days: int = 30
    request_timeout_seconds: float = 30.0

    # Optional fallback when the website blocks the crawler (free key: startup.jobs/api).
    startup_jobs_api_key: str = ""
    api_max_pages: int = Field(default=4, ge=1, le=20)

    @property
    def user_agent(self) -> str:
        return f"HBCrawler/{__version__} (+technical assessment; contact: {self.contact_email})"

    @property
    def cors_origin_list(self) -> list[str]:
        origins_list = []

        for origin in self.cors_origins.split(","):
            cleaned = origin.strip()

            if cleaned:  # If it's not an empty string
                origins_list.append(cleaned)
        return origins_list


@lru_cache
def get_settings() -> Settings:
    """Return one shared Settings object (created on first use)."""
    return Settings()
