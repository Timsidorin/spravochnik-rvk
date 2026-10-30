from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_login(value: str) -> str:
    """'DOMAIN\\user', 'user@domain' -> 'user' (в нижнем регистре)."""
    value = value.strip()
    if "\\" in value:
        value = value.rsplit("\\", 1)[1]
    if "@" in value:
        value = value.split("@", 1)[0]
    return value.strip().lower()


class Settings(BaseSettings):
    ad_server: str
    ad_user: str
    ad_password: str
    ad_search_base: str
    ad_departments_base: str = ""
    ad_domain: str = "RVK.local"
    ad_connect_timeout: int = 5
    ad_use_starttls: bool = False
    ad_ca_cert_file: str = ""
    ad_allow_insecure: bool = False

    ad_sync_enabled: bool = True
    ad_sync_times: str = "08:00,20:00"

    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    admin_users: str = ""

    login_max_failures_per_user: int = 5
    login_max_attempts_per_ip: int = 20
    login_window_seconds: int = 300

    enable_docs: bool = False

    database_url: str = "sqlite+aiosqlite:///./phonebook.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def ad_uses_ldaps(self) -> bool:
        return self.ad_server.strip().lower().startswith("ldaps://")

    @model_validator(mode="after")
    def _check_ldap_encryption(self):
        if not (self.ad_uses_ldaps or self.ad_use_starttls or self.ad_allow_insecure):
            raise ValueError(
                "Подключение к AD не зашифровано: пароли будут передаваться "
                "открытым текстом. Укажите AD_SERVER=ldaps://... или "
                "AD_USE_STARTTLS=true (либо временно AD_ALLOW_INSECURE=true)."
            )
        return self

    @property
    def admin_logins(self) -> set[str]:
        return {normalize_login(u) for u in self.admin_users.split(",") if u.strip()}


settings = Settings()