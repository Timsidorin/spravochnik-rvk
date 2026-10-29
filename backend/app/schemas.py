from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- Auth ----------
class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=1024)


class UserInfo(BaseModel):
    username: str
    is_admin: bool


class TokenResponse(UserInfo):
    pass


# ---------- Employee ----------
class EmployeeShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    full_name: str
    display_name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    ip_phone: Optional[str] = None
    sip_line: Optional[str] = None
    office: Optional[str] = None
    city: Optional[str] = None


# ---------- Department ----------
class DepartmentNode(BaseModel):
    id: int
    name: str
    head_login: Optional[str] = None
    employees_count: int = 0
    children: list["DepartmentNode"] = []


DepartmentNode.model_rebuild()


class DepartmentDetail(BaseModel):
    id: int
    name: str
    dn: str
    parent_id: Optional[int] = None
    head_login: Optional[str] = None
    head: Optional[EmployeeShort] = None
    employees: list[EmployeeShort] = []


class EmployeeDepartmentInfo(BaseModel):
    department_id: Optional[int] = None
    name: Optional[str] = None


# ---------- Search ----------
class SearchResult(BaseModel):
    employees: list[EmployeeShort] = []
    departments: list[DepartmentNode] = []


# ---------- Admin ----------
class ImportResult(BaseModel):
    departments: int
    employees: int


class StatusResult(BaseModel):
    departments: int
    employees: int