from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Department, Employee
from ..schemas import EmployeeDepartmentInfo, EmployeeShort

router = APIRouter(prefix="/api/employees", tags=["employees"])


async def _find(db: AsyncSession, login: str) -> Employee | None:
    return (
        await db.execute(select(Employee).where(Employee.login == login))
    ).scalar_one_or_none()


@router.get("/{login}", response_model=EmployeeShort)
async def get_employee(login: str, db: AsyncSession = Depends(get_db)):
    emp = await _find(db, login)
    if not emp:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    return emp


@router.get("/{login}/department", response_model=EmployeeDepartmentInfo)
async def get_employee_department(login: str, db: AsyncSession = Depends(get_db)):
    emp = await _find(db, login)
    dept = await db.get(Department, emp.department_id) if emp and emp.department_id else None
    if not dept:
        return EmployeeDepartmentInfo()
    return EmployeeDepartmentInfo(department_id=dept.id, name=dept.name)


@router.get("/{login}/photo")
async def get_employee_photo(login: str, db: AsyncSession = Depends(get_db)):
    photo = (
        await db.execute(select(Employee.photo).where(Employee.login == login))
    ).scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Фото не найдено")
    return Response(
        content=photo,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=300"},
    )
