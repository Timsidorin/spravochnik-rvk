import asyncio
import logging
from collections import Counter

from ldap3 import Connection, SUBTREE
from ldap3.core.exceptions import LDAPException
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .ldap_client import open_connection
from .models import Department, Employee

log = logging.getLogger(__name__)


# ============================================================
# Конфигурация
# ============================================================

IGNORED_OU_NAMES = {"fired", "disabled", "archive"}


def _get_departments_base() -> str:
    """
    Корень оргструктуры.
    Если ad_departments_base не задан — fallback на ad_search_base
    (фильтрация будет менее точной, но не упадёт).
    """
    return settings.ad_departments_base or settings.ad_search_base


# ============================================================
# Утилиты для работы с DN
# ============================================================

def _first(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value)


def _parse_dn(dn: str) -> list[tuple[str, str]]:
    if not dn:
        return []

    parts: list[str] = []
    buf = ""
    esc = False

    for ch in dn:
        if esc:
            buf += ch
            esc = False
        elif ch == "\\":
            buf += ch
            esc = True
        elif ch == ",":
            if buf.strip():
                parts.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        parts.append(buf.strip())

    result: list[tuple[str, str]] = []
    for p in parts:
        if "=" in p:
            k, _, v = p.partition("=")
            result.append((k.strip(), v.strip()))
    return result


def _build_dn(rdns: list[tuple[str, str]]) -> str:
    return ",".join(f"{k}={v}" for k, v in rdns)


def _dn_key(dn: str) -> tuple[tuple[str, str], ...]:
    return tuple((k.lower(), v.lower()) for k, v in _parse_dn(dn))


def _is_strictly_under(dn: str, base: str) -> bool:
    dn_key = _dn_key(dn)
    base_key = _dn_key(base)
    if not base_key:
        return True
    if len(dn_key) <= len(base_key):
        return False
    return dn_key[-len(base_key):] == base_key


def _is_valid_department_dn(dn: str) -> bool:
    base = _get_departments_base()
    if not _is_strictly_under(dn, base):
        return False
    for attr, val in _parse_dn(dn):
        if attr.lower() == "ou" and val.lower() in IGNORED_OU_NAMES:
            return False
    return True


def _extract_ou_chain(dn: str) -> list[tuple[str, str]]:
    rdns = _parse_dn(dn)
    result: list[tuple[str, str]] = []
    for i in range(len(rdns) - 1, -1, -1):
        attr, val = rdns[i]
        if attr.lower() == "ou":
            result.append((_build_dn(rdns[i:]), val))
    return result


# ============================================================
# Чтение из AD
# ============================================================

def _fetch_from_ad_sync() -> tuple[list[dict], dict[str, str]]:
    try:
        conn = open_connection(settings.ad_user, settings.ad_password)
    except LDAPException as e:
        raise RuntimeError(f"Не удалось подключиться к AD: {e}") from e

    try:
        users_raw = _fetch_users(conn)
        ou_map = _fetch_ou_map(conn)
        _merge_user_ous_into_map(users_raw, ou_map)
        log.info(
            "AD: прочитано пользователей=%d, отделов=%d",
            len(users_raw), len(ou_map),
        )
        return users_raw, ou_map
    finally:
        try:
            conn.unbind()
        except Exception:
            pass


def _fetch_users(conn: Connection) -> list[dict]:
    users: list[dict] = []
    for entry in conn.extend.standard.paged_search(
        search_base=settings.ad_search_base,
        search_filter=settings.ad_user_filter,
        search_scope=SUBTREE,
        attributes=[
            "sAMAccountName", "cn", "displayName", "mail", "title",
            "manager", "distinguishedName", "telephoneNumber", "mobile",
            "ipPhone", "otherTelephone", "msRTCSIP-Line",
            "physicalDeliveryOfficeName", "l",
        ],
        paged_size=1000,
        generator=True,
    ):
        if entry.get("type") == "searchResEntry":
            users.append(entry["attributes"])
    return users


def _fetch_ou_map(conn: Connection) -> dict[str, str]:
    ou_map: dict[str, str] = {}
    base = _get_departments_base()

    for entry in conn.extend.standard.paged_search(
        search_base=base,
        search_filter="(objectClass=organizationalUnit)",
        search_scope=SUBTREE,
        attributes=["ou", "distinguishedName"],
        paged_size=1000,
        generator=True,
    ):
        if entry.get("type") != "searchResEntry":
            continue
        attrs = entry["attributes"]
        dn = _first(attrs.get("distinguishedName"))

        if not dn or not _is_valid_department_dn(dn):
            continue

        ou_map[dn] = _first(attrs.get("ou")) or dn
    return ou_map


def _merge_user_ous_into_map(users_raw: list[dict], ou_map: dict[str, str]) -> None:
    for attrs in users_raw:
        dn = _first(attrs.get("distinguishedName"))
        for ou_dn, ou_name in _extract_ou_chain(dn):
            if _is_valid_department_dn(ou_dn):
                ou_map.setdefault(ou_dn, ou_name)


# ============================================================
# Построение отделов и сотрудников (в памяти, без обращений к БД)
# ============================================================

def _build_departments(ou_map: dict[str, str]) -> dict[str, Department]:
    dept_by_dn: dict[str, Department] = {}
    base_key = _dn_key(_get_departments_base())

    for dn in sorted(ou_map.keys(), key=lambda d: len(_parse_dn(d))):
        rdns = _parse_dn(dn)

        parent_dept: Department | None = None
        for i in range(1, len(rdns)):
            candidate_dn = _build_dn(rdns[i:])
            if candidate_dn in dept_by_dn:
                parent_dept = dept_by_dn[candidate_dn]
                break
            if _dn_key(candidate_dn) == base_key:
                break

        dept_by_dn[dn] = Department(name=ou_map[dn], dn=dn, parent=parent_dept)

    return dept_by_dn


def _resolve_department(
    dn: str, dept_by_dn: dict[str, Department]
) -> Department | None:
    for ou_dn, _ in reversed(_extract_ou_chain(dn)):
        dept = dept_by_dn.get(ou_dn)
        if dept is not None:
            return dept
    return None


def _build_employees(
    users_raw: list[dict],
    dept_by_dn: dict[str, Department],
) -> dict[str, Employee]:
    emp_by_login: dict[str, Employee] = {}
    emp_by_dn: dict[str, Employee] = {}

    for attrs in users_raw:
        login = _first(attrs.get("sAMAccountName"))
        if not login or login in emp_by_login:
            continue
        dn = _first(attrs.get("distinguishedName"))

        emp = Employee(
            login=login,
            full_name=_first(attrs.get("cn")) or login,
            display_name=_first(attrs.get("displayName")),
            email=_first(attrs.get("mail")),
            title=_first(attrs.get("title")),
            department=_resolve_department(dn, dept_by_dn),
            manager_dn=_first(attrs.get("manager")),
            phone=_first(attrs.get("telephoneNumber")),
            mobile=_first(attrs.get("mobile")),
            ip_phone=_first(attrs.get("ipPhone")),
            other_phone=_first(attrs.get("otherTelephone")),
            sip_line=_first(attrs.get("msRTCSIP-Line")),
            office=_first(attrs.get("physicalDeliveryOfficeName")),
            city=_first(attrs.get("l")),
            dn=dn or None,
        )
        emp_by_login[login] = emp
        if dn:
            emp_by_dn[dn] = emp

    for emp in emp_by_login.values():
        manager = emp_by_dn.get(emp.manager_dn) if emp.manager_dn else None
        if manager is not None:
            emp.manager_login = manager.login

    return emp_by_login


def _assign_department_heads(emp_by_login: dict[str, Employee]) -> None:
    managers_per_dept: dict[int, Counter] = {}
    direct_count: dict[int, int] = {}
    dept_by_key: dict[int, Department] = {}

    for emp in emp_by_login.values():
        dept = emp.department
        if dept is None:
            continue
        key = id(dept)
        dept_by_key[key] = dept
        direct_count[key] = direct_count.get(key, 0) + 1
        if emp.manager_login:
            managers_per_dept.setdefault(key, Counter())[emp.manager_login] += 1

    for key, counter in managers_per_dept.items():
        top_login, ref_count = counter.most_common(1)[0]
        if ref_count >= 2 or ref_count == direct_count.get(key, 0):
            dept_by_key[key].head_login = top_login


# ============================================================
# Точка входа
# ============================================================

async def import_from_ad(db: AsyncSession) -> dict:
    users_raw, ou_map = await asyncio.to_thread(_fetch_from_ad_sync)

    dept_by_dn = _build_departments(ou_map)
    emp_by_login = _build_employees(users_raw, dept_by_dn)
    _assign_department_heads(emp_by_login)

    # Всё в одной транзакции: при ошибке остаются прежние данные,
    # а читатели видят старый справочник до момента commit.
    try:
        await db.execute(delete(Employee))
        await db.execute(delete(Department))
        db.add_all(dept_by_dn.values())
        db.add_all(emp_by_login.values())
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return {
        "departments": len(dept_by_dn),
        "employees": len(emp_by_login),
    }
