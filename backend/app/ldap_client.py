import logging
import ssl

from ldap3 import (
    AUTO_BIND_NO_TLS,
    AUTO_BIND_TLS_BEFORE_BIND,
    NONE,
    Connection,
    Server,
    Tls,
)

from .config import settings

log = logging.getLogger(__name__)

if settings.ad_allow_insecure and not (settings.ad_uses_ldaps or settings.ad_use_starttls):
    log.warning(
        "AD_ALLOW_INSECURE=true: подключение к AD без шифрования, "
        "пароли передаются открытым текстом"
    )


def _make_server(address: str | None = None) -> Server:
    tls = Tls(
        validate=ssl.CERT_REQUIRED,
        ca_certs_file=settings.ad_ca_cert_file or None,
        ciphers=settings.ad_tls_ciphers or None,
    )
    address = address or settings.ad_server
    return Server(
        address,
        use_ssl=address.strip().lower().startswith("ldaps://"),
        tls=tls,
        get_info=NONE,
        connect_timeout=settings.ad_connect_timeout,
    )


def open_connection(user: str, password: str, write: bool = False) -> Connection:
    server = settings.ad_write_server if write and settings.ad_write_server else None
    auto_bind = (
        AUTO_BIND_TLS_BEFORE_BIND
        if settings.ad_use_starttls and not settings.ad_uses_ldaps
        else AUTO_BIND_NO_TLS
    )
    return Connection(
        _make_server(server),
        user=user,
        password=password,
        auto_bind=auto_bind,
        receive_timeout=settings.ad_connect_timeout,
    )
