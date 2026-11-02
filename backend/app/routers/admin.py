import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..ad_import import import_from_ad
from ..ad_write import set_photo, set_telephone
from ..photos import prepare_photo
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

    # Рабочий номер сразу пишем в AD; локально ничего не меняем, если запись не удалась
    if "phone" in data:
        if not emp.dn:
            raise HTTPException(
                status_code=409,
                detail="Сотрудник не привязан к AD, номер можно задать только в AD",
            )
        try:
            await asyncio.to_thread(
                set_telephone, emp.dn, (data["phone"] or "").strip() or None
            )
        except Exception:
            log.exception("Не удалось записать номер %s в AD (%s)", login, user.get("sub"))
            raise HTTPException(
                status_code=502,
                detail="Не удалось записать номер в AD, проверьте права учётной записи и логи сервера",
            )

    emp.manual_phone_fields = dump_manual_fields(
        manual_fields(emp) | (set(data) - {"phone"})
    )
    for field, value in data.items():
        setattr(emp, field, normalize_phone(value))

    await db.commit()
    log.info("Телефоны %s обновлены (%s): %s", login, user.get("sub"), data)
    return EmployeeShort.model_validate(emp)


@router.put("/employees/{login}/photo", response_model=EmployeeShort)
async def upload_photo(
    login: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    emp = (
        await db.execute(select(Employee).where(Employee.login == login))
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    if not emp.dn:
        raise HTTPException(status_code=409, detail="Сотрудник не привязан к AD")

    raw = await request.body()
    try:
        photo = prepare_photo(raw)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        await asyncio.to_thread(set_photo, emp.dn, photo)
    except Exception:
        log.exception("Не удалось записать фото %s в AD (%s)", login, user.get("sub"))
        raise HTTPException(
            status_code=502,
            detail="Не удалось записать фото в AD, проверьте права учётной записи",
        )

    emp.photo = photo
    await db.commit()
    log.info("Фото %s обновлено (%s)", login, user.get("sub"))
    return EmployeeShort.model_validate(emp)


@router.delete("/employees/{login}/photo", status_code=204)
async def delete_photo(
    login: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    emp = (
        await db.execute(select(Employee).where(Employee.login == login))
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    if not emp.dn:
        raise HTTPException(status_code=409, detail="Сотрудник не привязан к AD")

    try:
        await asyncio.to_thread(set_photo, emp.dn, None)
    except Exception:
        log.exception("Не удалось удалить фото %s из AD (%s)", login, user.get("sub"))
        raise HTTPException(status_code=502, detail="Не удалось удалить фото из AD")

    emp.photo = None
    await db.commit()
    log.info("Фото %s удалено (%s)", login, user.get("sub"))
    return Response(status_code=204)
