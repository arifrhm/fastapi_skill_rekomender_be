from datetime import datetime
from typing import List, Any
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pydantic import BaseModel, EmailStr

class Base(DeclarativeBase):
    pass

# Association tables
user_skills = Table(
    "users_skills_trial",
    Base.metadata,
    Column("user_skill_id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users_trial.user_id")),
    Column("skill_id", Integer, ForeignKey("skills_trial.skill_id")),
    Column("created_at", DateTime, default=datetime.utcnow)
)

position_skills = Table(
    "position_skills_trial",
    Base.metadata,
    Column("position_skill_id", Integer, primary_key=True),
    Column("position_id", Integer, ForeignKey("job_positions_trial.position_id")),
    Column("skill_id", Integer, ForeignKey("skills_trial.skill_id")),
    Column("created_at", DateTime, default=datetime.utcnow)
)

class User(Base):
    __tablename__ = "users_trial"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    job_title: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    skills = relationship("Skill", secondary=user_skills, back_populates="users")

class Skill(Base):
    __tablename__ = "skills_trial"

    skill_id: Mapped[int] = mapped_column(primary_key=True)
    skill_name: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", secondary=user_skills, back_populates="skills")
    positions = relationship("JobPosition", secondary=position_skills, back_populates="required_skills")

class JobPosition(Base):
    __tablename__ = "job_positions_trial"

    position_id: Mapped[int] = mapped_column(primary_key=True)
    job_title: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    required_skills = relationship("Skill", secondary=position_skills, back_populates="positions")

# Pydantic models for API
class UserBase(BaseModel):
    username: str
    email: EmailStr
    job_title: str

class UserCreate(UserBase):
    password: str
    skill_ids: List[int] = []

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    user_id: int

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
class SkillResponse(BaseModel):
    skill_id: int
    skill_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobPositionResponse(BaseModel):
    position_id: int
    job_title: str
    created_at: datetime
    updated_at: datetime
    required_skills: List[SkillResponse]

    class Config:
        from_attributes = True
