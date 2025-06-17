from typing import List, Any
from sqlalchemy import Column, Integer, String, ForeignKey, Table, Text, Enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pydantic import BaseModel, EmailStr

import enum


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"


# Association tables
user_skills = Table(
    "user_skills",
    Base.metadata,
    Column(
        "user_id",
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "skill_id",
        Integer,
        ForeignKey("skills.skill_id", ondelete="CASCADE"),
        primary_key=True
    )
)

job_skills = Table(
    "job_skills",
    Base.metadata,
    Column(
        "job_id",
        Integer,
        ForeignKey("jobs.job_id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "skill_id",
        Integer,
        ForeignKey("skills.skill_id", ondelete="CASCADE"),
        primary_key=True
    )
)

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "role_id",
        Integer,
        ForeignKey("roles.role_id", ondelete="CASCADE"),
        primary_key=True
    )
)


class Role(Base):
    __tablename__ = "roles"

    role_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role_name: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)

    users = relationship("User", secondary=user_roles, back_populates="roles")


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    job_title: Mapped[str] = mapped_column(String(100))

    skills = relationship("Skill", secondary=user_skills, back_populates="users")
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    audit_history = relationship("AuditHistory", back_populates="user", cascade="all, delete-orphan")


class Skill(Base):
    __tablename__ = "skills"

    skill_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    skill_name: Mapped[str] = mapped_column(String(255), unique=True)

    users = relationship("User", secondary=user_skills, back_populates="skills")
    jobs = relationship(
        "Job", 
        secondary=job_skills, 
        back_populates="required_skills"
    )


class Job(Base):
    __tablename__ = "jobs"

    job_id: Mapped[int] = mapped_column(primary_key=True)
    job_title: Mapped[str] = mapped_column(Text)
    job_detail_link: Mapped[str] = mapped_column(Text)
    company: Mapped[str] = mapped_column(Text)
    locations: Mapped[str] = mapped_column(Text)
    job_details: Mapped[str] = mapped_column(Text)

    required_skills = relationship(
        "Skill", 
        secondary=job_skills, 
        back_populates="jobs"
    )


# Pydantic models for API
class RoleBase(BaseModel):
    role_name: str
    description: str | None = None


class RoleCreate(RoleBase):
    pass


class RoleResponse(RoleBase):
    role_id: int

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    username: str
    email: EmailStr
    job_title: str


class UserCreate(UserBase):
    password: str
    skill_ids: List[int] = []
    role_id: int = 1  # Default to USER role (ID: 1)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class SkillResponse(BaseModel):
    skill_id: int
    skill_name: str

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    user_id: int
    skills: List[SkillResponse] = []
    role: RoleResponse

    class Config:
        from_attributes = True


# Pagination models
class PaginatedResponse(BaseModel):
    total: int
    page: int
    size: int
    pages: int
    items: List[Any]

    class Config:
        from_attributes = True


# Pydantic models for API responses
class JobResponse(BaseModel):
    job_id: int
    job_title: str
    job_detail_link: str
    company: str | None = None
    locations: str
    job_details: str
    required_skills: List[SkillResponse]

    class Config:
        from_attributes = True


class AuditHistory(Base):
    __tablename__ = "audit_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    ip_address: Mapped[str] = mapped_column(String(50))
    recommendation_result: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(50))  # Store timestamp as string

    user = relationship("User", back_populates="audit_history")


class AuditHistoryResponse(BaseModel):
    id: int
    user_id: int
    ip_address: str
    recommendation_result: str
    created_at: str
    username: str

    class Config:
        from_attributes = True
