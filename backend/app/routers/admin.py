from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Department, Employee
from ..ad_import import import_from_ad
from ..auth import require_admin
from ..schemas import ImportResult, StatusResult

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/import", response_model=ImportResult)
async def trigger_import(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_admin),
):
    try:
        result = await import_from_ad(db)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка импорта: {e}")

    return ImportResult(**result)


@router.get("/status", response_model=StatusResult)
async def status(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_admin),
):
    dept_count = (
        await db.execute(select(func.count(Department.id)))
    ).scalar() or 0
    emp_count = (
        await db.execute(select(func.count(Employee.id)))
    ).scalar() or 0

    return StatusResult(departments=dept_count, employees=emp_count)