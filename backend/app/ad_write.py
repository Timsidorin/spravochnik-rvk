import logging
from contextlib import suppress

from ldap3 import MODIFY_DELETE, MODIFY_REPLACE

from .config import settings
from .ldap_client import open_connection

log = logging.getLogger(__name__)


def set_telephone(dn: str, value: str | None) -> None:
    """Пишет telephoneNumber в AD. None — удалить атрибут. Синхронно, из thread pool."""
    conn = open_connection(settings.ad_user, settings.ad_password, write=True)
    try:
        changes = {
            "telephoneNumber": [
                (MODIFY_REPLACE, [value]) if value else (MODIFY_DELETE, [])
            ]
        }
        if not conn.modify(dn, changes):
            raise RuntimeError(str(conn.result))
    finally:
        with suppress(Exception):
            conn.unbind()
