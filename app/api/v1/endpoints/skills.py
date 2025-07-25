from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.models import Skill, User, PaginatedResponse, SkillResponse
from app.api.v1.endpoints.users import get_current_user
from sqlalchemy.orm import selectinload

router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def get_skills(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: str = Query(None, description="Search term for skill name"),
    session: AsyncSession = Depends(get_session),
):
    # Calculate offset
    offset = (page - 1) * size

    # Base query
    base_query = select(Skill).order_by(Skill.skill_name.asc())
    
    # Add search filter if search term is provided
    if search:
        base_query = base_query.where(Skill.skill_name.ilike(f"%{search}%"))

    # Get total count with search filter
    count_query = select(func.count()).select_from(base_query.subquery())
    total = await session.scalar(count_query)

    # Get paginated items with search filter
    query = base_query.offset(offset).limit(size)
    result = await session.execute(query)
    items = result.scalars().all()

    # Calculate total pages
    pages = (total + size - 1) // size

    # Convert SQLAlchemy models to Pydantic models
    skill_responses = [SkillResponse.model_validate(skill) for skill in items]

    return {
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "items": skill_responses,
    }


@router.post("/", response_model=SkillResponse)
async def create_skill(
    skill_name: str,
    db: AsyncSession = Depends(get_session),
):
    # Capitalize first letter of skill name
    skill_name = skill_name.capitalize()
    
    # Check if skill already exists (case-insensitive)
    query = select(Skill).where(Skill.skill_name.ilike(skill_name)).limit(1)
    result = await db.execute(query)
    existing_skill = result.first()
    
    if existing_skill:
        return SkillResponse.model_validate(existing_skill[0].__dict__)
    
    # Create new skill if it doesn't exist
    new_skill = Skill(skill_name=skill_name)
    db.add(new_skill)
    await db.commit()
    await db.refresh(new_skill)
    
    return SkillResponse.model_validate(new_skill.__dict__)


@router.post("/user/{skill_id}")
async def add_user_skill(
    skill_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Reload user with skills relationship
    query = (
        select(User)
        .options(selectinload(User.skills))
        .where(User.user_id == current_user.user_id)
    )
    result = await session.execute(query)
    user = result.scalar_one()

    # Check if skill exists
    query = select(Skill).where(Skill.skill_id == skill_id)
    result = await session.execute(query)
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found"
        )

    # Check if user already has this skill
    if skill in user.skills:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has this skill",
        )

    # Add skill to user
    user.skills.append(skill)
    await session.commit()

    return {"message": "Skill added successfully"}


@router.delete("/user/{skill_id}")
async def remove_user_skill(
    skill_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Reload user with skills relationship
    query = (
        select(User)
        .options(selectinload(User.skills))
        .where(User.user_id == current_user.user_id)
    )
    result = await session.execute(query)
    user = result.scalar_one()

    # Check if skill exists
    query = select(Skill).where(Skill.skill_id == skill_id)
    result = await session.execute(query)
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found"
        )

    # Check if user has this skill
    if skill not in user.skills:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not have this skill",
        )

    # Remove skill from user
    user.skills.remove(skill)
    await session.commit()

    return {"message": "Skill removed successfully"}
