from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./avatar.db"

    # --- LLM providers -------------------------------------------------------
    # LLM_PROVIDER: auto (nvidia if NVIDIA_API_KEY, else anthropic if ANTHROPIC_API_KEY) | nvidia | anthropic
    llm_provider: str = "auto"
    llm_mode: str = "auto"  # auto | demo  (demo forces the deterministic heuristic fallbacks)
    # NVIDIA NIM hosted API (OpenAI-compatible): Nemotron
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model_fast: str = "nvidia/nemotron-3.5-lightning-30b-a3b"  # classification / extraction
    nvidia_model_smart: str = "nvidia/nemotron-3-ultra-550b-a55b"  # drafting, agents, reports
    nvidia_timeout: int = 120
    llm_daily_call_limit: int = 0  # 0 = unlimited; when reached, agents fall back to heuristics until tomorrow (UTC)
    # Anthropic (optional alternative)
    anthropic_api_key: str = ""
    anthropic_model_fast: str = "claude-haiku-5-5"
    anthropic_model_smart: str = "claude-sonnet-5-5"

    jwt_secret: str = "dev-secret-change-me"
    jwt_expire_minutes: int = 720
    ingest_key: str = "dev-ingest-key"  # shared secret for the email webhook
    seed_demo: bool = True
    inline_jobs: bool = False  # run jobs synchronously (tests)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # business thresholds (deterministic rules)
    lot_cluster_threshold: int = 3  # complaints on one lot within 30d -> escalate
    recurring_issue_threshold: int = 5  # complaints in one issue within 14d -> recurring
    similarity_threshold: float = 0.42

    @property
    def provider(self) -> str:
        """'nvidia' | 'anthropic' | '' (no usable provider / demo mode)."""
        if self.llm_mode == "demo":
            return ""
        p = self.llm_provider.lower()
        if p == "nvidia":
            return "nvidia" if self.nvidia_api_key else ""
        if p == "anthropic":
            return "anthropic" if self.anthropic_api_key else ""
        if self.nvidia_api_key:
            return "nvidia"
        return "anthropic" if self.anthropic_api_key else ""

    @property
    def llm_live(self) -> bool:
        return bool(self.provider)

    @property
    def engine_name(self) -> str:
        return {"nvidia": "nemotron", "anthropic": "claude"}.get(self.provider, "heuristic")

    @property
    def model_fast(self) -> str:
        return self.nvidia_model_fast if self.provider == "nvidia" else self.anthropic_model_fast

    @property
    def model_smart(self) -> str:
        return self.nvidia_model_smart if self.provider == "nvidia" else self.anthropic_model_smart


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
