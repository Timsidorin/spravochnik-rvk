from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_AD_USER_FILTER = (
    "(&(objectCategory=person)(objectClass=user)"
    "(!(sAMAccountName=*$))"
    "(!(userAccountControl:1.2.840.113556.1.4.803:=2)))"
)

INSECURE_JWT_SECRETS = {"", "change-me", "secret", "changeme"}


class Settings(BaseSettings):
    ad_server: str
    ad_user: str
    ad_password: str
    ad_search_base: str
    ad_departments_base: str = ""
    ad_domain: str = "RVK.local"
    ad_user_filter: str = DEFAULT_AD_USER_FILTER

    ad_start_tls: bool = False
    ad_tls_validate: bool = True
    ad_ca_certs_file: str = ""
    ad_timeout_seconds: int = 10

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    auth_cookie_name: str = "phonebook_token"
    auth_cookie_secure: bool = False

    admin_users: str = ""

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = "sqlite+aiosqlite:///./phonebook.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("jwt_secret")
    @classmethod
    def _check_jwt_secret(cls, v: str) -> str:
        if v.strip().lower() in INSECURE_JWT_SECRETS or len(v) < 32:
            raise ValueError(
                "JWT_SECRET должен быть случайной строкой длиной не менее 32 символов"
            )
        return v

    @field_validator("database_url")
    @classmethod
    def _force_async_sqlite(cls, v: str) -> str:
        if v.startswith("sqlite://"):
            return "sqlite+aiosqlite://" + v[len("sqlite://"):]
        return v

    @property
    def admin_logins(self) -> set[str]:
        return {u.strip().lower() for u in self.admin_users.split(",") if u.strip()}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ad_uses_tls(self) -> bool:
        return self.ad_server.lower().startswith("ldaps://") or self.ad_start_tls


settings = Settings()
