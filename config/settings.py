from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # AI API Keys
    ANTHROPIC_API_KEY: str
    PERPLEXITY_API_KEY: str
    DEEPSEEK_API_KEY: str
    VOYAGE_API_KEY: str

    # Local database paths
    CHROMA_PERSIST_DIR: str = Field(default="./data/chromadb")
    CHROMA_COLLECTION_NAME: str = Field(default="linkedin_knowledge")
    SQLITE_DB_PATH: str = Field(default="./data/content_agent.db")

    # Google Drive sync
    GDRIVE_ENABLED: bool = Field(default=False)
    GDRIVE_FOLDER_ID: str = Field(default="")
    GDRIVE_CREDENTIALS_PATH: str = Field(default="./config/gdrive_credentials.json")

    # App config
    LOG_LEVEL: str = Field(default="INFO")
    MAX_RETRIES: int = Field(default=1)

    # Test mode — swaps all models to cheapest equivalents to minimise API spend
    TEST_MODE: bool = Field(default=False)


# Singleton instance — import this everywhere
settings = Settings()
