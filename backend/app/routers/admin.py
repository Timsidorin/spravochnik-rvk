import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..ad_import import import_from_ad
from ..auth import require_admin
from ..database import get_db
from ..models import Employee
from ..phones import dump_manual_fields, manual_fields, normalize_phone
from ..schemas import EmployeeShort, ImportResult, PhoneUpdate

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/import", response_model=ImportResult)
async def trigger_import(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    try:
        result = await import_from_ad(db)
    except Exception:
        await db.rollback()
        log.exception("Ошибка импорта из AD (запустил %s)", user.get("sub"))
        raise HTTPException(
            status_code=500,
            detail="Ошибка импорта из AD, подробности в журнале сервера",
        )

    log.info("Импорт из AD выполнен (%s): %s", user.get("sub"), result)
    return ImportResult(**result)


@router.put("/employees/{login}/phones", response_model=EmployeeShort)
async def update_phones(
    login: str,
    payload: PhoneUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    emp = (
        await db.execute(select(Employee).where(Employee.login == login))
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    data = payload.model_dump(exclude_unset=True)
    emp.manual_phone_fields = dump_manual_fields(manual_fields(emp) | set(data))
    for field, value in data.items():
        setattr(emp, field, normalize_phone(value))

    await db.commit()
    log.info("Телефоны %s обновлены (%s): %s", login, user.get("sub"), data)
    return EmployeeShort.model_validate(emp)
