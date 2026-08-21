from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "db"
    postgres_port: int = 5432

    session_cookie_name: str = "session_id"
    session_timeout_minutes: int = 30
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "strict"

    rate_limit_max_attempts: int = 5
    rate_limit_window_minutes: int = 5
    rate_limit_lockout_minutes: int = 5

    app_env: str = "production-like"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
