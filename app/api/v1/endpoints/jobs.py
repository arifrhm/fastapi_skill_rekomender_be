from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy import select, func, or_, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Tuple, Optional
from pydantic import BaseModel
from datetime import datetime
import json

from app.models import (
    Job,
    Skill,
    User,
    JobResponse,
    PaginatedResponse,
    AuditHistory,
)
from app.api.v1.endpoints.users import get_current_user
from app.database import get_session
from app.utils.skill_recommender import (
    JOB_TITLE_VARIATIONS,
    recommend_skills,
    llr_similarity,
)

router = APIRouter()


# Response Models
class SkillInfo(BaseModel):
    skill_id: int
    skill_name: str


class JobSkills(BaseModel):
    matching: List[SkillInfo]
    recommended: List[SkillInfo]


class JobRecommendation(BaseModel):
    position_id: int
    job_title: str
    log_likelihood: float
    skills: JobSkills


class TopRecommendationResponse(BaseModel):
    job: Optional[JobRecommendation]
    message: Optional[str] = None


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
    total = await session.scalar(select(func.count()).select_from(Job))
    # Get paginated items with relationships loaded
    query = (
        select(Job)
        .options(selectinload(Job.required_skills))
        .offset(offset)
        .limit(size)
    )
    result = await session.execute(query)
    items = result.scalars().all()
    # Calculate total pages
    pages = (total + size - 1) // size

    # Convert to Pydantic models
    job_responses = [JobResponse.model_validate(job) for job in items]

    return {
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "items": job_responses,
    }


@router.post("/", response_model=JobResponse)
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
    job = Job(job_title=job_title)
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Add required skills
    job.required_skills.extend(skills)
    await session.commit()

    # Reload job with relationships
    query = (
        select(Job)
        .options(selectinload(Job.required_skills))
        .where(Job.job_id == job.job_id)
    )
    result = await session.execute(query)
    job = result.scalar_one()

    return JobResponse.model_validate(job)


async def find_similar_users(
    user_id: int, session: AsyncSession, top_n: int
) -> List[Tuple[User, float]]:
    """
    Find users with similar skills to the given user.
    Returns a list of tuples containing (user, similarity_score).
    """
    # Get current user's skills
    stmt = (
        select(User).options(
            selectinload(User.skills)).where(User.user_id == user_id)
    )
    result = await session.execute(stmt)
    current_user = result.scalar_one_or_none()

    if not current_user:
        return []

    current_user_skills = {skill.skill_id for skill in current_user.skills}

    # Get all users except current user with their skills
    stmt = (
        select(User).options(
            selectinload(User.skills)).where(User.user_id != user_id)
    )
    result = await session.execute(stmt)
    users = result.scalars().all()

    # Calculate similarity scores
    similar_users = []
    for user in users:
        user_skills = {skill.skill_id for skill in user.skills}

        # Calculate Jaccard similarity
        intersection = len(current_user_skills & user_skills)
        union = len(current_user_skills | user_skills)

        if union > 0:
            similarity = intersection / union
            similar_users.append((user, similarity))

    # Sort by similarity score and return top N
    similar_users.sort(key=lambda x: x[1], reverse=True)
    return similar_users[:top_n]


@router.get(
    "/top-recommendation",
    summary="Get top job recommendation",
    description="""
    Get the top 1 job recommendation based on log likelihood score.

    The recommendation is based on:
    1. Job title similarity with user's current job
    2. Skill matching using log likelihood

    Returns:
    - Best matching job with:
        - Job details (ID, title)
        - Log likelihood score
        - Matching skills (skills user already has)
        - Recommended skills (skills user needs to learn)
    """,
)
async def get_top_job_recommendation(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get top job recommendation based on
    authenticated user's skills using LLS similarity.
    """
    print("\n=== Starting Job Recommendation Process ===")

    # Get user's skills with proper async loading
    query = (
        select(User)
        .options(selectinload(User.skills))
        .where(User.user_id == current_user.user_id)
    )
    result = await session.execute(query)
    user = result.scalar_one()

    user_skills = [skill.skill_name for skill in user.skills]

    print("\nUser Info:")
    print(f"User ID: {user.user_id}")
    print(f"Full Name: {user.full_name}")
    print(f"Job Title: {user.job_title}")
    print(f"User Skills: {user_skills}")

    # Find matching job title variations
    job_title_variations = []
    matched_category = None
    for category, variations in JOB_TITLE_VARIATIONS.items():
        for variation in variations:
            if variation.lower() == user.job_title.lower():
                print(
                    f"Found matching job title variation: {variation}"
                    f" in category: {category}"
                )
                job_title_variations = JOB_TITLE_VARIATIONS.get(category)
                matched_category = category
                break
        if matched_category:
            break

    if job_title_variations:
        print(f"\nJob title variations to search: {job_title_variations}")
    else:
        print("\nNo matching job title variations found, will search all jobs")

    # Get all unique skills from the database for universe calculation
    all_skills_query = select(distinct(Skill.skill_name))
    all_skills_result = await session.execute(all_skills_query)
    all_skills = [skill[0] for skill in all_skills_result.fetchall()]

    print(f"\nTotal unique skills in database: {len(all_skills)}")

    # Get jobs with their skills, filtered by job title if variations found
    jobs_query = select(Job).options(selectinload(Job.required_skills))

    if job_title_variations:
        # Include jobs that match any variation from the matched category
        title_filters = []
        for variation in job_title_variations:
            title_filters.append(Job.job_title.ilike(f"%{variation}%"))

        jobs_query = jobs_query.where(or_(*title_filters))

        # Print the SQL query for debugging
        print("\nSQL Query:")
        print(str(jobs_query))

    result = await session.execute(jobs_query)
    jobs = result.scalars().all()

    print(f"\nFound {len(jobs)} matching jobs")
    if jobs:
        print("\nMatching jobs:")
        for job in jobs:
            print(f"- {job.job_title}")

    # Calculate LLS for each job
    max_lls_value = float("-inf")
    best_job = None
    best_job_skills = None
    job_scores = []

    print("\nCalculating LLS scores for all jobs:")
    for job in jobs:
        job_skills = [skill.skill_name for skill in job.required_skills]
        lls_value = llr_similarity(
            user_skills,
            job_skills,
            universe=all_skills
        )

        print(
            f"Job: {job.job_title} |"
            f" Skills: {job_skills} | LLS: {lls_value:.4f}"
        )

        job_scores.append(
            {
                "job_id": job.job_id,
                "title": job.job_title,
                "skills": job_skills,
                "lls_score": lls_value,
            }
        )

        if lls_value > max_lls_value:
            max_lls_value = lls_value
            best_job = job
            best_job_skills = job_skills
            print("*** New Best Match! ***")

    if not best_job:
        print("\nNo matching jobs found!")
        return {
            "message": "No matching job positions found",
            "job": None,
            "log_likelihood": 0,
            "recommended_skills": [],
        }

    print("\nBest Matching Job:")
    print(f"Title: {best_job.job_title}")
    print(f"Log Likelihood Score: {max_lls_value:.4f}")
    print(f"Required Skills: {best_job_skills}")

    # Get recommended skills
    recommended_skill_names = recommend_skills(user_skills, best_job_skills)
    print(f"\nRecommended Skills: {recommended_skill_names}")

    # Get skill details for recommended skills
    if recommended_skill_names:
        query = select(Skill).where(Skill.skill_name.in_(
            recommended_skill_names
        ))
        result = await session.execute(query)
        recommended_skills = result.scalars().all()
        print("\nRecommended Skills Details:")
        for skill in recommended_skills:
            print(f"- {skill.skill_name} (ID: {skill.skill_id})")
    else:
        recommended_skills = []
        print("\nNo recommended skills found")

    # Get matching skills
    matching_skills = [
        skill for skill in best_job.required_skills
        if skill.skill_name in user_skills
    ]

    print("\nMatching Skills:")
    for skill in matching_skills:
        print(f"- {skill.skill_name}")

    print("\n=== End of Job Recommendation Process ===\n")

    # Prepare recommendation result
    recommendation_result = {
        "job": {
            "job_id": best_job.job_id,
            "job_title": best_job.job_title,
            "log_likelihood": round(max_lls_value, 4),
            "skills": {
                "matching": [
                    {
                        "skill_id": skill.skill_id,
                        "skill_name": skill.skill_name,
                    }
                    for skill in matching_skills
                ],
                "recommended": [
                    {
                        "skill_id": skill.skill_id,
                        "skill_name": skill.skill_name,
                    }
                    for skill in recommended_skills
                ],
            },
        },
        "all_job_scores": sorted(
            job_scores, key=lambda x: x["lls_score"], reverse=True
        )[:10],
    }

    # Log audit history
    client_host = request.client.host if request.client else "unknown"
    audit_entry = AuditHistory(
        user_id=current_user.user_id,
        ip_address=client_host,
        recommendation_result=json.dumps(recommendation_result),
        created_at=datetime.now().isoformat()
    )
    session.add(audit_entry)
    await session.commit()

    return recommendation_result
