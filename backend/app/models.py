from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from .database import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    dn = Column(String, unique=True, index=True, nullable=False)
    parent_id = Column(
        Integer,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    head_login = Column(String, nullable=True)

    parent = relationship("Department", remote_side=[id], backref="children")
    employees = relationship(
        "Employee",
        back_populates="department",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Department {self.name}>"


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True)
    login = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    display_name = Column(String)
    email = Column(String)
    title = Column(String)

    department_id = Column(
        Integer,
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    manager_dn = Column(String)
    manager_login = Column(String)

    phone = Column(String)
    mobile = Column(String)
    ip_phone = Column(String)
    other_phone = Column(String)
    sip_line = Column(String)
    office = Column(String)
    city = Column(String)

    dn = Column(String, unique=True, index=True)
    synced_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    department = relationship("Department", back_populates="employees")

    def __repr__(self) -> str:
        return f"<Employee {self.login}>"