import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import is_superadmin, require_superadmin
from ..config import normalize_login, settings
from ..database import get_db
from ..models import Admin, Employee
from ..schemas import AdminIn, AdminOut

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/admins", tags=["admin"])


async def _full_names(db: AsyncSession, logins: set[str]) -> dict[str, str]:
    if not logins:
        return {}
    rows = await db.execute(
        select(func.lower(Employee.login), Employee.full_name)
        .where(func.lower(Employee.login).in_(logins))
    )
    return dict(rows.all())


@router.get("", response_model=list[AdminOut])
async def list_admins(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_superadmin),
):
    db_admins = (await db.execute(select(Admin).order_by(Admin.login))).scalars().all()
    env_logins = sorted(settings.admin_logins)
    names = await _full_names(db, set(env_logins) | {a.login for a in db_admins})

    return [
        *(AdminOut(login=l, full_name=names.get(l), from_env=True) for l in env_logins),
        *(
            AdminOut(login=a.login, full_name=names.get(a.login), from_env=False, added_by=a.added_by)
            for a in db_admins
            if a.login not in settings.admin_logins
        ),
    ]


@router.post("", response_model=AdminOut, status_code=201)
async def add_admin(
    payload: AdminIn,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    login = normalize_login(payload.login)
    if not login:
        raise HTTPException(status_code=422, detail="Укажите логин")
    if is_superadmin(login) or await db.scalar(select(Admin.id).where(Admin.login == login)):
        raise HTTPException(status_code=409, detail=f"{login} уже администратор")

    names = await _full_names(db, {login})
    if login not in names:
        raise HTTPException(
            status_code=404,
            detail=f"Сотрудник с логином {login} не найден в справочнике",
        )

    db.add(Admin(login=login, added_by=user["sub"]))
    await db.commit()
    log.info("Администратор %s добавлен (%s)", login, user["sub"])
    return AdminOut(login=login, full_name=names[login], from_env=False, added_by=user["sub"])


@router.delete("/{login}", status_code=204)
async def remove_admin(
    login: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    login = normalize_login(login)
    if is_superadmin(login):
        raise HTTPException(
            status_code=400,
            detail="Администратора из настроек сервера можно убрать только в .env",
        )
    admin = (await db.execute(select(Admin).where(Admin.login == login))).scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="Администратор не найден")

    await db.delete(admin)
    await db.commit()
    log.info("Администратор %s удалён (%s)", login, user["sub"])
    return Response(status_code=204)
