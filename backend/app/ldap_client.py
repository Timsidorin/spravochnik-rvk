import ssl

from ldap3 import (
    ALL,
    AUTO_BIND_NO_TLS,
    AUTO_BIND_TLS_BEFORE_BIND,
    Connection,
    Server,
    Tls,
)

from .config import settings


def _make_server() -> Server:
    tls = Tls(
        validate=ssl.CERT_REQUIRED if settings.ad_tls_validate else ssl.CERT_NONE,
        ca_certs_file=settings.ad_ca_certs_file or None,
    )
    return Server(
        settings.ad_server,
        get_info=ALL,
        tls=tls,
        connect_timeout=settings.ad_timeout_seconds,
    )


def open_connection(user: str, password: str) -> Connection:
    """Bind к AD; при AD_START_TLS=true сначала выполняется StartTLS."""
    return Connection(
        _make_server(),
        user=user,
        password=password,
        auto_bind=AUTO_BIND_TLS_BEFORE_BIND if settings.ad_start_tls else AUTO_BIND_NO_TLS,
        receive_timeout=settings.ad_timeout_seconds,
    )
