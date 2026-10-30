from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=256)
    # Пустой пароль в LDAP — анонимный bind, который AD может принять
    password: str = Field(min_length=1, max_length=256)


class UserInfo(BaseModel):
    username: str
    is_admin: bool
    is_superadmin: bool


class TokenResponse(UserInfo):
    access_token: str
    token_type: str = "bearer"


class AdminIn(BaseModel):
    login: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]


class AdminOut(BaseModel):
    login: str
    full_name: Optional[str] = None
    from_env: bool
    added_by: Optional[str] = None


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


class SearchResult(BaseModel):
    employees: list[EmployeeShort] = []
    departments: list[DepartmentNode] = []


class QuickContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    sort_order: int = 0


class QuickContactIn(BaseModel):
    name: Name
    phone: Phone


class QuickContactPatch(BaseModel):
    name: Optional[Name] = None
    phone: Optional[Phone] = None


class PhoneUpdate(BaseModel):
    phone: Optional[str] = Field(default=None, max_length=64)
    mobile: Optional[str] = Field(default=None, max_length=64)
    ip_phone: Optional[str] = Field(default=None, max_length=64)
    other_phone: Optional[str] = Field(default=None, max_length=64)
    sip_line: Optional[str] = Field(default=None, max_length=128)


class ImportResult(BaseModel):
    departments: int
    employees: int
