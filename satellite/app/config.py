import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    port: int = 8001
    storage_root: str = os.getenv("STORAGE_ROOT", os.getenv("DATA_DIR", "/data/storage"))
    stac_url: str = os.getenv("STAC_URL", "https://earth-search.aws.element84.com/v1")
    stac_collection: str = os.getenv("STAC_COLLECTION", "sentinel-2-l2a")
    satellite_mode: str = os.getenv("SATELLITE_MODE", "real")
    min_aoi_km2: float = float(os.getenv("MIN_AOI_KM2", "0.25"))
    max_cloud_cover: float = float(os.getenv("MAX_CLOUD", "20.0"))
    date_window_days: int = int(os.getenv("DATE_WINDOW_DAYS", "30"))


settings = Settings()
