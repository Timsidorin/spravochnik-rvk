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


def _make_server() -> Server:
    tls = Tls(
        validate=ssl.CERT_REQUIRED,
        ca_certs_file=settings.ad_ca_cert_file or None,
    )
    return Server(
        settings.ad_server,
        use_ssl=settings.ad_uses_ldaps,
        tls=tls,
        get_info=NONE,
        connect_timeout=settings.ad_connect_timeout,
    )


def open_connection(user: str, password: str) -> Connection:
    """Bind к AD с обязательным шифрованием (LDAPS или StartTLS), если оно
    не отключено явно через AD_ALLOW_INSECURE."""
    auto_bind = (
        AUTO_BIND_TLS_BEFORE_BIND
        if settings.ad_use_starttls and not settings.ad_uses_ldaps
        else AUTO_BIND_NO_TLS
    )
    return Connection(
        _make_server(),
        user=user,
        password=password,
        auto_bind=auto_bind,
        receive_timeout=settings.ad_connect_timeout,
    )
