from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ad_server: str
    ad_user: str
    ad_password: str
    ad_search_base: str
    ad_departments_base: str = ""
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    admin_users: str = ""

    database_url: str = "sqlite+aiosqlite:///./phonebook.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def admin_logins(self) -> set[str]:
        return {u.strip().lower() for u in self.admin_users.split(",") if u.strip()}


settings = Settings()