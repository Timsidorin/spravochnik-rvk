import asyncio
import logging
from collections import Counter

from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPException
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .models import Department, Employee

log = logging.getLogger(__name__)


# ---------- Утилиты для работы с атрибутами и DN ----------

def _first(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value)


def _parse_dn(dn: str) -> list[tuple[str, str]]:
    """Разбирает DN на список RDN [(attr, value), ...] от листа к корню."""
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
    """Собирает DN из RDN-списка (обратная операция к _parse_dn)."""
    return ",".join(f"{k}={v}" for k, v in rdns)


def _dn_key(dn: str) -> tuple[tuple[str, str], ...]:
    """Нормализованный ключ DN для сравнения без учёта регистра."""
    return tuple((k.lower(), v.lower()) for k, v in _parse_dn(dn))


def _is_under_base(dn: str, base: str) -> bool:
    """Проверяет, что dn находится внутри base (или равен ему)."""
    dn_key = _dn_key(dn)
    base_key = _dn_key(base)
    if not base_key:
        return True
    if len(dn_key) < len(base_key):
        return False
    return dn_key[-len(base_key):] == base_key


def _is_valid_department_dn(dn: str) -> bool:
    """
    Проверяет, является ли OU бизнес-отделом.
    Отсеивает системные ветки верхнего уровня (Groups, Computers и т.д.).
    """
    rdns = _parse_dn(dn)
    if not rdns:
        return False

    # Игнорируемые инфраструктурные папки
    ignored_branches = {"groups", "computers", "servers", "services_accounts"}
    
    # Ищем самый верхний OU (первый после базового DC/OU)
    for attr, val in reversed(rdns):
        if attr.lower() == "ou":
            if val.lower() in ignored_branches:
                return False
            break  # Проверили верхний уровень, дальше нет смысла
            
    return True


def _extract_ou_chain(dn: str) -> list[tuple[str, str]]:
    """[(full_ou_dn, ou_name), ...] для всех OU в DN, от корня к листьям."""
    rdns = _parse_dn(dn)
    result: list[tuple[str, str]] = []
    for i in range(len(rdns) - 1, -1, -1):
        attr, val = rdns[i]
        if attr.lower() == "ou":
            result.append((_build_dn(rdns[i:]), val))
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
        users_raw = _fetch_users(conn)
        ou_map = _fetch_ou_map(conn)
        _merge_user_ous_into_map(users_raw, ou_map)
        log.info("AD: прочитано пользователей=%d, OU под базой=%d",
                 len(users_raw), len(ou_map))
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
        search_filter="(&(objectClass=user)(!(sAMAccountName=*$)))",
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
    """Карта {full_ou_dn: ou_name} для OU строго под search_base."""
    ou_map: dict[str, str] = {}
    base = settings.ad_search_base

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
        
        if not dn or not _is_under_base(dn, base) or not _is_valid_department_dn(dn):
            continue
            
        ou_map[dn] = _first(attrs.get("ou")) or dn
    return ou_map


def _merge_user_ous_into_map(users_raw: list[dict], ou_map: dict[str, str]) -> None:
    """Дополняет карту OU из DN пользователей, но только валидные OU."""
    base = settings.ad_search_base
    for attrs in users_raw:
        dn = _first(attrs.get("distinguishedName"))
        for ou_dn, ou_name in _extract_ou_chain(dn):
            if _is_under_base(ou_dn, base) and _is_valid_department_dn(ou_dn):
                ou_map.setdefault(ou_dn, ou_name)


# ---------- Построение отделов и сотрудников ----------

async def _build_departments(
    db: AsyncSession, ou_map: dict[str, str]
) -> dict[str, Department]:
    """Создаёт отделы от корня к листьям, заполняет parent_id."""
    dept_by_dn: dict[str, Department] = {}

    # Родители должны идти раньше детей — сортируем по числу RDN.
    for dn in sorted(ou_map.keys(), key=lambda d: len(_parse_dn(d))):
        rdns = _parse_dn(dn)
        parent_dn = _build_dn(rdns[1:]) if len(rdns) > 1 else None

        dept = Department(name=ou_map[dn], dn=dn)
        if parent_dn:
            parent = dept_by_dn.get(parent_dn)
            if parent is not None:
                dept.parent_id = parent.id
            else:
                log.debug("Родитель для %s не найден среди OU (%s)", dn, parent_dn)

        db.add(dept)
        await db.flush()
        dept_by_dn[dn] = dept

    await db.commit()
    return dept_by_dn


def _resolve_department_id(
    dn: str, dept_by_dn: dict[str, Department]
) -> int | None:
    """Ближайший (самый глубокий) OU пользователя, зарегистрированный как отдел."""
    for ou_dn, _ in reversed(_extract_ou_chain(dn)):
        dept = dept_by_dn.get(ou_dn)
        if dept is not None:
            return dept.id
    return None


async def _build_employees(
    db: AsyncSession,
    users_raw: list[dict],
    dept_by_dn: dict[str, Department],
) -> tuple[dict[str, Employee], dict[str, Employee]]:
    emp_by_login: dict[str, Employee] = {}
    emp_by_dn: dict[str, Employee] = {}

    for attrs in users_raw:
        login = _first(attrs.get("sAMAccountName"))
        if not login:
            continue
        dn = _first(attrs.get("distinguishedName"))

        emp = Employee(
            login=login,
            full_name=_first(attrs.get("cn")) or login,
            display_name=_first(attrs.get("displayName")),
            email=_first(attrs.get("mail")),
            title=_first(attrs.get("title")),
            department_id=_resolve_department_id(dn, dept_by_dn),
            manager_dn=_first(attrs.get("manager")),
            phone=_first(attrs.get("telephoneNumber")),
            mobile=_first(attrs.get("mobile")),
            ip_phone=_first(attrs.get("ipPhone")),
            other_phone=_first(attrs.get("otherTelephone")),
            sip_line=_first(attrs.get("msRTCSIP-Line")),
            office=_first(attrs.get("physicalDeliveryOfficeName")),
            city=_first(attrs.get("l")),
            dn=dn,
        )
        db.add(emp)
        await db.flush()
        emp_by_login[login] = emp
        if dn:
            emp_by_dn[dn] = emp

    await db.commit()
    return emp_by_login, emp_by_dn


async def _resolve_managers(
    db: AsyncSession,
    emp_by_login: dict[str, Employee],
    emp_by_dn: dict[str, Employee],
) -> None:
    """Резолвит manager DN → manager_login."""
    for emp in emp_by_login.values():
        if emp.manager_dn and emp.manager_dn in emp_by_dn:
            emp.manager_login = emp_by_dn[emp.manager_dn].login
    await db.commit()


async def _assign_department_heads(
    db: AsyncSession,
    dept_by_dn: dict[str, Department],
    emp_by_login: dict[str, Employee],
) -> None:
    """Определяет руководителя отдела по самому частому manager_login."""
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

    await db.commit()


# ---------- Точка входа ----------

async def import_from_ad(db: AsyncSession) -> dict:
    # 1. Чтение AD в отдельном потоке (ldap3 синхронный).
    users_raw, ou_map = await asyncio.to_thread(_fetch_from_ad_sync)

    # 2. Полная перезагрузка.
    await db.execute(delete(Employee))
    await db.execute(delete(Department))
    await db.commit()

    # 3. Отделы.
    dept_by_dn = await _build_departments(db, ou_map)

    # 4. Сотрудники.
    emp_by_login, emp_by_dn = await _build_employees(db, users_raw, dept_by_dn)

    # 5. manager DN → manager_login.
    await _resolve_managers(db, emp_by_login, emp_by_dn)

    # 6. Руководители отделов.
    await _assign_department_heads(db, dept_by_dn, emp_by_login)

    return {
        "departments": len(dept_by_dn),
        "employees": len(emp_by_login),
    }