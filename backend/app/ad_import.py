import asyncio
import logging
from collections import Counter
from contextlib import suppress

from ldap3 import Connection, SUBTREE
from ldap3.core.exceptions import LDAPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .ldap_client import open_connection
from .models import Department, Employee
from .phones import AD_PHONE_ATTRS, dump_manual_fields, manual_fields, normalize_phone

log = logging.getLogger(__name__)

IGNORED_OU_NAMES = {"fired", "disabled", "archive"}


def _departments_base() -> str:
    return settings.ad_departments_base or settings.ad_search_base


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


def _in_ignored_ou(dn: str) -> bool:
    return any(
        attr.lower() == "ou" and val.lower() in IGNORED_OU_NAMES
        for attr, val in _parse_dn(dn)
    )


def _is_valid_department_dn(dn: str) -> bool:
    return _is_strictly_under(dn, _departments_base()) and not _in_ignored_ou(dn)


def _extract_ou_chain(dn: str) -> list[tuple[str, str]]:
    rdns = _parse_dn(dn)
    result: list[tuple[str, str]] = []
    for i in range(len(rdns) - 1, -1, -1):
        attr, val = rdns[i]
        if attr.lower() == "ou":
            result.append((_build_dn(rdns[i:]), val))
    return result


def _fetch_from_ad_sync() -> tuple[list[dict], dict[str, str]]:
    try:
        conn = open_connection(settings.ad_user, settings.ad_password)
    except LDAPException as e:
        raise RuntimeError(f"Не удалось подключиться к AD: {e}") from e

    try:
        users_raw = _fetch_users(conn)
        ou_map = _fetch_ou_map(conn)
        _merge_user_ous_into_map(users_raw, ou_map)
        log.info("AD: прочитано пользователей=%d, отделов=%d", len(users_raw), len(ou_map))
        return users_raw, ou_map
    finally:
        with suppress(Exception):
            conn.unbind()


def _fetch_users(conn: Connection) -> list[dict]:
    users: list[dict] = []
    for entry in conn.extend.standard.paged_search(
        search_base=settings.ad_search_base,
        search_filter=(
            "(&(objectCategory=person)(objectClass=user)"
            "(!(sAMAccountName=*$))"
            "(!(userAccountControl:1.2.840.113556.1.4.803:=2)))"
        ),
        search_scope=SUBTREE,
        attributes=[
            "sAMAccountName", "cn", "displayName", "mail", "title",
            "manager", "distinguishedName",
            *AD_PHONE_ATTRS.values(),
            "physicalDeliveryOfficeName", "l",
        ],
        paged_size=1000,
        generator=True,
    ):
        if entry.get("type") != "searchResEntry":
            continue
        attrs = entry["attributes"]
        if _in_ignored_ou(_first(attrs.get("distinguishedName"))):
            continue
        users.append(attrs)
    return users


def _fetch_ou_map(conn: Connection) -> dict[str, str]:
    ou_map: dict[str, str] = {}
    for entry in conn.extend.standard.paged_search(
        search_base=_departments_base(),
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
        if dn and _is_valid_department_dn(dn):
            ou_map[dn] = _first(attrs.get("ou")) or dn
    return ou_map


def _merge_user_ous_into_map(users_raw: list[dict], ou_map: dict[str, str]) -> None:
    for attrs in users_raw:
        dn = _first(attrs.get("distinguishedName"))
        for ou_dn, ou_name in _extract_ou_chain(dn):
            if _is_valid_department_dn(ou_dn):
                ou_map.setdefault(ou_dn, ou_name)


async def _build_departments(
    db: AsyncSession, ou_map: dict[str, str]
) -> dict[str, Department]:
    dept_by_dn: dict[str, Department] = {}
    base_key = _dn_key(_departments_base())

    for dn in sorted(ou_map, key=lambda d: len(_parse_dn(d))):
        rdns = _parse_dn(dn)

        parent: Department | None = None
        for i in range(1, len(rdns)):
            candidate_dn = _build_dn(rdns[i:])
            if candidate_dn in dept_by_dn:
                parent = dept_by_dn[candidate_dn]
                break
            if _dn_key(candidate_dn) == base_key:
                break

        dept = Department(name=ou_map[dn], dn=dn, parent_id=parent.id if parent else None)
        db.add(dept)
        await db.flush()
        dept_by_dn[dn] = dept

    return dept_by_dn


def _resolve_department_id(
    dn: str, dept_by_dn: dict[str, Department]
) -> int | None:
    for ou_dn, _ in reversed(_extract_ou_chain(dn)):
        dept = dept_by_dn.get(ou_dn)
        if dept is not None:
            return dept.id
    return None


async def _snapshot_manual_phones(db: AsyncSession) -> dict[str, dict[str, str | None]]:
    """Ручные телефоны по логину, включая намеренно стёртые (None)."""
    rows = await db.execute(
        select(
            Employee.login,
            Employee.manual_phone_fields,
            *(getattr(Employee, f) for f in AD_PHONE_ATTRS),
        )
    )
    result: dict[str, dict[str, str | None]] = {}
    for row in rows:
        if fields := manual_fields(row):
            result[row.login] = {f: getattr(row, f) for f in fields}
    return result


def _ad_phones(attrs: dict) -> dict[str, str | None]:
    return {f: normalize_phone(_first(attrs.get(a))) for f, a in AD_PHONE_ATTRS.items()}


async def _build_employees(
    db: AsyncSession,
    users_raw: list[dict],
    dept_by_dn: dict[str, Department],
    manual_phones: dict[str, dict[str, str | None]],
) -> tuple[dict[str, Employee], dict[str, Employee]]:
    emp_by_login: dict[str, Employee] = {}
    emp_by_dn: dict[str, Employee] = {}

    for attrs in users_raw:
        login = _first(attrs.get("sAMAccountName"))
        if not login:
            continue
        dn = _first(attrs.get("distinguishedName"))

        manual = manual_phones.get(login, {})
        emp = Employee(
            login=login,
            full_name=_first(attrs.get("cn")) or login,
            display_name=_first(attrs.get("displayName")),
            email=_first(attrs.get("mail")),
            title=_first(attrs.get("title")),
            department_id=_resolve_department_id(dn, dept_by_dn),
            manager_dn=_first(attrs.get("manager")),
            office=_first(attrs.get("physicalDeliveryOfficeName")),
            city=_first(attrs.get("l")),
            dn=dn or None,
            manual_phone_fields=dump_manual_fields(set(manual)),
            **{**_ad_phones(attrs), **manual},
        )
        db.add(emp)
        emp_by_login[login] = emp
        if dn:
            emp_by_dn[dn] = emp

    await db.flush()
    return emp_by_login, emp_by_dn


def _resolve_managers(
    emp_by_login: dict[str, Employee],
    emp_by_dn: dict[str, Employee],
) -> None:
    for emp in emp_by_login.values():
        if emp.manager_dn and emp.manager_dn in emp_by_dn:
            emp.manager_login = emp_by_dn[emp.manager_dn].login


def _assign_department_heads(
    dept_by_dn: dict[str, Department],
    emp_by_login: dict[str, Employee],
) -> None:
    managers_per_dept: dict[int, Counter] = {}
    direct_count: dict[int, int] = {}

    for emp in emp_by_login.values():
        if not emp.department_id:
            continue
        direct_count[emp.department_id] = direct_count.get(emp.department_id, 0) + 1
        if emp.manager_login:
            managers_per_dept.setdefault(emp.department_id, Counter())[
                emp.manager_login
            ] += 1

    for dept in dept_by_dn.values():
        counter = managers_per_dept.get(dept.id)
        if not counter:
            continue
        top_login, ref_count = counter.most_common(1)[0]
        total = direct_count.get(dept.id, 0)
        if ref_count >= 2 or ref_count == total:
            dept.head_login = top_login


async def import_from_ad(db: AsyncSession) -> dict:
    """Полная пересинхронизация в одной транзакции; при ошибке вызывающий делает rollback."""
    users_raw, ou_map = await asyncio.to_thread(_fetch_from_ad_sync)
    manual_phones = await _snapshot_manual_phones(db)

    await db.execute(delete(Employee))
    await db.execute(delete(Department))

    dept_by_dn = await _build_departments(db, ou_map)
    emp_by_login, emp_by_dn = await _build_employees(
        db, users_raw, dept_by_dn, manual_phones
    )
    _resolve_managers(emp_by_login, emp_by_dn)
    _assign_department_heads(dept_by_dn, emp_by_login)
    await db.commit()
    return {"departments": len(dept_by_dn), "employees": len(emp_by_login)}