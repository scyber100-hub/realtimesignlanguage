import os
from functools import lru_cache


class Settings:
    app_name: str = "Realtime KOR→KSL Pipeline"
    version: str = os.getenv("APP_VERSION", "0.2.0")
    cors_allow_origins: str = os.getenv("CORS_ALLOW_ORIGINS", "*")
    default_start_ms: int = int(os.getenv("DEFAULT_START_MS", "0"))
    default_gap_ms: int = int(os.getenv("DEFAULT_GAP_MS", "60"))
    api_key: str | None = os.getenv("API_KEY")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    enable_metrics: bool = os.getenv("ENABLE_METRICS", "1") == "1"
    lexicon_path: str | None = os.getenv("LEXICON_PATH")
    include_aux_channels: bool = os.getenv("INCLUDE_AUX_CHANNELS", "1") == "1"
    max_ingest_rps: int = int(os.getenv("MAX_INGEST_RPS", "20"))
    session_ttl_s: int = int(os.getenv("SESSION_TTL_S", "600"))
    # Alert thresholds
    latency_p90_warn_ms: int = int(os.getenv("LATENCY_P90_WARN_MS", "1200"))
    replace_ratio_warn: float = float(os.getenv("REPLACE_RATIO_WARN", "0.5"))
    rate_limit_ratio_warn: float = float(os.getenv("RATE_LIMIT_RATIO_WARN", "0.1"))
    # Replace tuning
    replace_min_events: int = int(os.getenv("REPLACE_MIN_EVENTS", "2"))
    replace_min_ms: int = int(os.getenv("REPLACE_MIN_MS", "300"))
    replace_min_interval_ms: int = int(os.getenv("REPLACE_MIN_INTERVAL_MS", "150"))


@lru_cache
def get_settings() -> Settings:
    # load .env if present
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv()
    except Exception:
        pass
    return Settings()
