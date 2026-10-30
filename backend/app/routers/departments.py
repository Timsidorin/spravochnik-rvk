from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Department, Employee
from ..schemas import DepartmentNode, DepartmentDetail, EmployeeShort, SearchResult

router = APIRouter(prefix="/api/departments", tags=["departments"])


async def _employee_counts(db: AsyncSession) -> dict[int, int]:
    rows = await db.execute(
        select(Employee.department_id, func.count(Employee.id))
        .where(Employee.department_id.isnot(None))
        .group_by(Employee.department_id)
    )
    return dict(rows.all())


@router.get("/tree", response_model=list[DepartmentNode])
async def get_tree(db: AsyncSession = Depends(get_db)):
    depts = (await db.execute(select(Department))).scalars().all()
    counts = await _employee_counts(db)

    nodes: dict[int, dict] = {}
    for d in depts:
        nodes[d.id] = {
            "id": d.id,
            "name": d.name,
            "head_login": d.head_login,
            "employees_count": counts.get(d.id, 0),
            "parent_id": d.parent_id,
            "children": [],
        }

    roots: list[dict] = []
    for node in nodes.values():
        pid = node.pop("parent_id", None)
        if pid and pid in nodes:
            nodes[pid]["children"].append(node)
        else:
            roots.append(node)

    return roots


@router.get("/search", response_model=SearchResult)
async def search(
    q: str = Query(max_length=100),
    db: AsyncSession = Depends(get_db),
):
    needle = q.strip().lower()
    if not needle:
        return SearchResult()

    def match(column):
        return func.lower(column).contains(needle, autoescape=True)

    searchable = (
        Employee.full_name,
        Employee.login,
        Employee.email,
        Employee.phone,
        Employee.mobile,
        Employee.ip_phone,
        Employee.other_phone,
        Employee.title,
    )
    employees = (
        await db.execute(
            select(Employee)
            .where(or_(*(match(c) for c in searchable)))
            .order_by(Employee.full_name)
            .limit(50)
        )
    ).scalars().all()

    departments = (
        await db.execute(
            select(Department)
            .where(match(Department.name))
            .order_by(Department.name)
            .limit(20)
        )
    ).scalars().all()

    dept_counts = await _employee_counts(db)

    return SearchResult(
        employees=[EmployeeShort.model_validate(e) for e in employees],
        departments=[
            DepartmentNode(
                id=d.id,
                name=d.name,
                head_login=d.head_login,
                employees_count=dept_counts.get(d.id, 0),
            )
            for d in departments
        ],
    )


@router.get("/{dept_id}", response_model=DepartmentDetail)
async def get_department(dept_id: int, db: AsyncSession = Depends(get_db)):
    dept = await db.get(Department, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Отдел не найден")

    all_emps = (
        await db.execute(
            select(Employee)
            .where(Employee.department_id == dept.id)
            .order_by(Employee.full_name)
        )
    ).scalars().all()

    head = next((e for e in all_emps if e.login == dept.head_login), None)
    others = [e for e in all_emps if e is not head]

    return DepartmentDetail(
        id=dept.id,
        name=dept.name,
        parent_id=dept.parent_id,
        head_login=dept.head_login,
        head=EmployeeShort.model_validate(head) if head else None,
        employees=[EmployeeShort.model_validate(e) for e in others],
    )