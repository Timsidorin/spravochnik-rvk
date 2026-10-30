import logging
from contextlib import suppress

from ldap3 import MODIFY_DELETE, MODIFY_REPLACE

from .config import settings
from .ldap_client import open_connection

log = logging.getLogger(__name__)


def _modify(dn: str, changes: dict) -> None:
    conn = open_connection(settings.ad_user, settings.ad_password, write=True)
    try:
        if not conn.modify(dn, changes):
            raise RuntimeError(str(conn.result))
    finally:
        with suppress(Exception):
            conn.unbind()


def set_telephone(dn: str, value: str | None) -> None:
    op = (MODIFY_REPLACE, [value]) if value else (MODIFY_DELETE, [])
    _modify(dn, {"telephoneNumber": [op]})


def set_photo(dn: str, data: bytes | None) -> None:
    op = (MODIFY_REPLACE, [data]) if data else (MODIFY_DELETE, [])
    _modify(dn, {"thumbnailPhoto": [op]})
