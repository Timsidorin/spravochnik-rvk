from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Employee, Department
from ..schemas import EmployeeShort, EmployeeDepartmentInfo
from ..auth import get_current_user

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get("/{login}", response_model=EmployeeShort)
async def get_employee(
    login: str,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    emp = (
        await db.execute(select(Employee).where(Employee.login == login))
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    return EmployeeShort.model_validate(emp)


@router.get("/{login}/department", response_model=EmployeeDepartmentInfo)
async def get_employee_department(
    login: str,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    emp = (
        await db.execute(select(Employee).where(Employee.login == login))
    ).scalar_one_or_none()
    if not emp or not emp.department_id:
        return EmployeeDepartmentInfo()

    dept = (
        await db.execute(select(Department).where(Department.id == emp.department_id))
    ).scalar_one_or_none()
    if not dept:
        return EmployeeDepartmentInfo()

    return EmployeeDepartmentInfo(department_id=dept.id, name=dept.name)