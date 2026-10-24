from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env", env_file_encoding="utf-8",
        extra="ignore", hide_input_in_errors=True,
    )
    data_mode: Literal["fixture", "postgis"] = "fixture"
    database_url: SecretStr | None = Field(default=None, repr=False)
    database_host: str = ""
    database_port: int = Field(default=5432, ge=1, le=65535)
    database_name: str = "postgres"
    database_user: str = ""
    database_password: SecretStr | None = Field(default=None, repr=False)
    database_ssl_mode: Literal["require", "verify-full"] = "require"
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    request_limit_per_minute: int = 120
    geoai_enabled: bool = True
    geoai_provider: Literal["disabled", "openai_compatible"] = "disabled"
    geoai_api_key: SecretStr | None = Field(default=None, repr=False)
    geoai_base_url: str = "https://api.openai.com/v1"
    geoai_model: str = Field(default="", max_length=100)
    geoai_timeout_s: int = Field(default=25, ge=5, le=45)
    optimization_enabled: bool = True
    analytics_enabled: bool = True
    routing_enabled: bool = True
    routing_provider: Literal["osrm","disabled"] = "osrm"
    routing_base_url: str = "https://routing.openstreetmap.de/routed-car"
    routing_osrm_profile: str = Field(default="driving", pattern="^[a-z_]{1,20}$")
    routing_provider_label: str = Field(default="FOSSGIS public demo",max_length=60)
    routing_policy_url: str = "https://routing.openstreetmap.de/about.html"
    discovery_enabled: bool = True
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    geocoding_url: str = "https://nominatim.openstreetmap.org/search"
    osm_user_agent: str = "LogistiMapAI/0.3 (local Malaysian industrial GIS research)"
    provider_cache_dir: Path = BACKEND_ROOT / ".cache" / "providers"
    fixture_path: Path = PROJECT_ROOT / "data" / "fixtures" / "synthetic.geojson"

    @field_validator("database_url", "database_password", mode="before")
    @classmethod
    def empty_secret(cls, value):
        if value == "" or (isinstance(value, SecretStr) and value.get_secret_value() == ""):
            return None
        return value

    @property
    def database_configured(self) -> bool:
        return bool(self.database_url or (
            self.database_host and self.database_user and self.database_name and self.database_password
        ))

    @field_validator("request_limit_per_minute")
    @classmethod
    def valid_limit(cls, value: int) -> int:
        if not 10 <= value <= 10000:
            raise ValueError("Request limit must be between 10 and 10000")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
