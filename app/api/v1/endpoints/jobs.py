from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List

from app.models import JobPosition, Skill, User, JobPositionResponse, PaginatedResponse
from app.api.v1.endpoints.users import get_current_user
from app.database import get_session

router = APIRouter()


# get all jobs with pagination
@router.get("/", response_model=PaginatedResponse)
async def get_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
):
    # Calculate offset
    offset = (page - 1) * size

    # Get total count
    total = await session.scalar(select(func.count()).select_from(JobPosition))

    # Get paginated items with relationships loaded
    query = (
        select(JobPosition)
        .options(selectinload(JobPosition.required_skills))
        .offset(offset)
        .limit(size)
    )
    result = await session.execute(query)
    items = result.scalars().all()

    # Calculate total pages
    pages = (total + size - 1) // size

    # Convert to Pydantic models
    job_responses = [JobPositionResponse.model_validate(job) for job in items]

    return {
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "items": job_responses,
    }


@router.post("/", response_model=JobPositionResponse)
async def create_job(
    job_title: str,
    skill_ids: List[int],
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Verify all skills exist
    query = select(Skill).where(Skill.skill_id.in_(skill_ids))
    result = await session.execute(query)
    skills = result.scalars().all()

    if len(skills) != len(skill_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more skills not found",
        )

    # Create job position
    job = JobPosition(job_title=job_title)
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Add required skills
    job.required_skills.extend(skills)
    await session.commit()

    # Reload job with relationships
    query = (
        select(JobPosition)
        .options(selectinload(JobPosition.required_skills))
        .where(JobPosition.job_id == job.job_id)
    )
    result = await session.execute(query)
    job = result.scalar_one()

    return JobPositionResponse.model_validate(job)


@router.get("/recommendations", response_model=List[JobPositionResponse])
async def get_job_recommendations(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Get all jobs with their required skills
    query = select(JobPosition).options(selectinload(JobPosition.required_skills))
    result = await session.execute(query)
    jobs = result.scalars().all()

    # Calculate match percentages
    job_data = []
    for job in jobs:
        required_skills = set(skill.skill_id for skill in job.required_skills)
        user_skill_ids = set(skill.skill_id for skill in current_user.skills)

        matching_skills = len(user_skill_ids & required_skills)
        match_percentage = (
            matching_skills / len(required_skills) * 100 if required_skills else 0
        )

        job_data.append({"job": job, "match_percentage": match_percentage})

    # Sort by match percentage
    job_data.sort(key=lambda x: x["match_percentage"], reverse=True)

    # Return top 10 matching jobs
    return [JobPositionResponse.model_validate(item["job"]) for item in job_data[:10]]
