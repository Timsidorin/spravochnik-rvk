import asyncio
from collections import Counter

from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPException
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .models import Department, Employee


# ---------- Утилиты для работы с атрибутами и DN ----------

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


def _extract_ou_chain(dn: str) -> list[tuple[str, str]]:
    """Возвращает [(full_ou_dn, ou_name), ...] для всех OU в DN, сверху вниз."""
    rdns = _parse_dn(dn)
    result: list[tuple[str, str]] = []
    for i in range(len(rdns) - 1, -1, -1):
        attr, val = rdns[i]
        if attr.lower() == "ou":
            full_dn = ",".join(f"{a}={v}" for a, v in rdns[i:])
            result.append((full_dn, val))
    return result


# ---------- Синхронное чтение из AD (в отдельном thread) ----------

def _fetch_from_ad_sync() -> tuple[list[dict], dict[str, str]]:
    """Синхронно читает пользователей и OU. Возвращает (users_raw, ou_name_map)."""
    server = Server(settings.ad_server, get_info=ALL)

    try:
        conn = Connection(
            server,
            user=settings.ad_user,
            password=settings.ad_password,
            auto_bind=True,
        )
    except LDAPException as e:
        raise RuntimeError(f"Не удалось подключиться к AD: {e}")

    try:
        users_raw: list[dict] = []
        for entry in conn.extend.standard.paged_search(
            search_base=settings.ad_search_base,
            search_filter="(&(objectClass=user)(!(sAMAccountName=*$)))",
            search_scope=SUBTREE,
            attributes=[
                "sAMAccountName",
                "cn",
                "displayName",
                "mail",
                "title",
                "manager",
                "distinguishedName",
                "telephoneNumber",
                "mobile",
                "ipPhone",
                "otherTelephone",
                "msRTCSIP-Line",
                "physicalDeliveryOfficeName",
                "l",
            ],
            paged_size=1000,
            generator=True,
        ):
            if entry.get("type") == "searchResEntry":
                users_raw.append(entry["attributes"])

        ou_name_map: dict[str, str] = {}
        for entry in conn.extend.standard.paged_search(
            search_base=settings.ad_search_base,
            search_filter="(objectClass=organizationalUnit)",
            search_scope=SUBTREE,
            attributes=["ou", "distinguishedName"],
            paged_size=1000,
            generator=True,
        ):
            if entry.get("type") == "searchResEntry":
                a = entry["attributes"]
                dn = _first(a.get("distinguishedName"))
                name = _first(a.get("ou"))
                if dn:
                    ou_name_map[dn] = name or dn

        for a in users_raw:
            dn = _first(a.get("distinguishedName"))
            for ou_dn, ou_name in _extract_ou_chain(dn):
                ou_name_map.setdefault(ou_dn, ou_name)

        return users_raw, ou_name_map
    finally:
        try:
            conn.unbind()
        except Exception:
            pass


# ---------- Async-версия импорта ----------

async def import_from_ad(db: AsyncSession) -> dict:
    # 1. Чтение AD в отдельном потоке
    users_raw, ou_name_map = await asyncio.to_thread(_fetch_from_ad_sync)

    # 2. Очистка существующих данных
    await db.execute(delete(Employee))
    await db.execute(delete(Department))
    await db.commit()

    # 3. Отделы: от корня к листьям
    dept_by_dn: dict[str, Department] = {}
    for dn in sorted(ou_name_map.keys(), key=lambda d: -d.count(",")):
        name = ou_name_map[dn]
        rdns = _parse_dn(dn)
        parent_dn = ",".join(f"{a}={v}" for a, v in rdns[1:]) if len(rdns) > 1 else None

        dept = Department(name=name, dn=dn)
        if parent_dn and parent_dn in dept_by_dn:
            dept.parent_id = dept_by_dn[parent_dn].id
        db.add(dept)
        await db.flush()
        dept_by_dn[dn] = dept

    await db.commit()

    # 4. Сотрудники
    emp_by_login: dict[str, Employee] = {}
    emp_by_dn: dict[str, Employee] = {}

    for a in users_raw:
        login = _first(a.get("sAMAccountName"))
        if not login:
            continue
        dn = _first(a.get("distinguishedName"))

        dept_id = None
        for ou_dn, _ in reversed(_extract_ou_chain(dn)):
            if ou_dn in dept_by_dn:
                dept_id = dept_by_dn[ou_dn].id
                break

        emp = Employee(
            login=login,
            full_name=_first(a.get("cn")) or login,
            display_name=_first(a.get("displayName")),
            email=_first(a.get("mail")),
            title=_first(a.get("title")),
            department_id=dept_id,
            manager_dn=_first(a.get("manager")),
            phone=_first(a.get("telephoneNumber")),
            mobile=_first(a.get("mobile")),
            ip_phone=_first(a.get("ipPhone")),
            other_phone=_first(a.get("otherTelephone")),
            sip_line=_first(a.get("msRTCSIP-Line")),
            office=_first(a.get("physicalDeliveryOfficeName")),
            city=_first(a.get("l")),
            dn=dn,
        )
        db.add(emp)
        await db.flush()
        emp_by_login[login] = emp
        if dn:
            emp_by_dn[dn] = emp

    await db.commit()

    # 5. Резолвим manager DN → manager_login
    for emp in emp_by_login.values():
        if emp.manager_dn and emp.manager_dn in emp_by_dn:
            emp.manager_login = emp_by_dn[emp.manager_dn].login
    await db.commit()

    # 6. Определяем руководителей отделов
    managers_per_dept: dict[int, Counter] = {}
    for emp in emp_by_login.values():
        if emp.department_id and emp.manager_login:
            managers_per_dept.setdefault(emp.department_id, Counter())[emp.manager_login] += 1

    direct_count: dict[int, int] = {}
    for emp in emp_by_login.values():
        if emp.department_id:
            direct_count[emp.department_id] = direct_count.get(emp.department_id, 0) + 1

    for dept in dept_by_dn.values():
        counter = managers_per_dept.get(dept.id)
        if not counter:
            continue
        top_login, ref_count = counter.most_common(1)[0]
        total = direct_count.get(dept.id, 0)
        if ref_count >= 2 or ref_count == total:
            dept.head_login = top_login

    await db.commit()

    return {
        "departments": len(dept_by_dn),
        "employees": len(emp_by_login),
    }