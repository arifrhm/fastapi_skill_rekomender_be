from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import polars as pl

from app.models import (
    JobPosition,
    User,
    Skill,
    PositionSkill,
    JobPosition_Pydantic
)
from app.api.v1.endpoints.users import get_current_user

router = APIRouter()


@router.get("/", response_model=List[JobPosition_Pydantic])
async def get_jobs():
    return await JobPosition_Pydantic.from_queryset(JobPosition.all())


@router.post("/", response_model=JobPosition_Pydantic)
async def create_job(
    job_title: str,
    skill_ids: List[int],
    current_user: User = Depends(get_current_user)
):
    # Verify all skills exist
    skills = await Skill.filter(skill_id__in=skill_ids)
    if len(skills) != len(skill_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more skills not found"
        )
    
    job = await JobPosition.create(job_title=job_title)
    
    # Add required skills
    for skill in skills:
        await PositionSkill.create(
            position=job,
            skill=skill
        )
    
    return await JobPosition_Pydantic.from_tortoise_orm(job)


@router.get("/recommendations", response_model=List[JobPosition_Pydantic])
async def get_job_recommendations(
    current_user: User = Depends(get_current_user)
):
    # Get user's skills
    user_skills = await current_user.user_skills.all().prefetch_related('skill')
    user_skill_ids = [us.skill.skill_id for us in user_skills]
    
    # Get all jobs with their required skills
    jobs = await JobPosition.all().prefetch_related('position_skills__skill')
    
    # Use Polars for efficient data processing
    job_data = []
    for job in jobs:
        required_skills = [
            ps.skill.skill_id
            for ps in job.position_skills
        ]
        matching_skills = len(
            set(user_skill_ids) & set(required_skills)
        )
        match_percentage = (
            matching_skills / len(required_skills) * 100
            if required_skills else 0
        )
        
        job_data.append({
            "job": job,
            "match_percentage": match_percentage
        })
    
    # Sort by match percentage
    job_data.sort(
        key=lambda x: x["match_percentage"],
        reverse=True
    )
    
    # Return top 10 matching jobs
    return [
        await JobPosition_Pydantic.from_tortoise_orm(item["job"])
        for item in job_data[:10]
    ] 