from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- Auth ----------
class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=256)
    # Пустой пароль в LDAP означает анонимный (unauthenticated) bind,
    # который AD может принять — поэтому запрещаем его явно.
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    is_admin: bool


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
    other_phone: Optional[str] = None
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


# ---------- Quick contacts ----------
class QuickContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    sort_order: int = 0


class QuickContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    phone: str = Field(min_length=1, max_length=64)
    sort_order: int = 0


class QuickContactPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    phone: Optional[str] = Field(default=None, min_length=1, max_length=64)
    sort_order: Optional[int] = None


# ---------- Admin ----------
class PhoneUpdate(BaseModel):
    phone: Optional[str] = Field(default=None, max_length=64)
    mobile: Optional[str] = Field(default=None, max_length=64)
    ip_phone: Optional[str] = Field(default=None, max_length=64)
    other_phone: Optional[str] = Field(default=None, max_length=64)
    sip_line: Optional[str] = Field(default=None, max_length=128)


class ImportResult(BaseModel):
    departments: int
    employees: int


class StatusResult(BaseModel):
    departments: int
    employees: int