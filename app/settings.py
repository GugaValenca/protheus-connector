from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Protheus Connector"
    APP_ENV: str = "dev"
    APP_API_KEY: str

    DATABASE_URL: str = "sqlite:///./app.db"

    PROTHEUS_BASE_URL: str
    PROTHEUS_USERNAME: str
    PROTHEUS_PASSWORD: str
    PROTHEUS_TIMEOUT_S: float = 30.0

settings = Settings()
