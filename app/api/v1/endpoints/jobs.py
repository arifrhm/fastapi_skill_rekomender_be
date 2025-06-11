from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Tuple

from app.models import JobPosition, Skill, User, JobPositionResponse, PaginatedResponse
from app.api.v1.endpoints.users import get_current_user
from app.database import get_session
from app.utils.skill_recommender import (
    JOB_TITLE_VARIATIONS,
    log_likelihood,
    recommend_skills,
)

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


async def find_similar_users(
    user_id: int, session: AsyncSession, top_n: int
) -> List[Tuple[User, float]]:
    """
    Find users with similar skills to the given user.
    Returns a list of tuples containing (user, similarity_score).
    """
    # Get current user's skills
    stmt = (
        select(User).options(selectinload(User.skills)).where(User.user_id == user_id)
    )
    result = await session.execute(stmt)
    current_user = result.scalar_one_or_none()

    if not current_user:
        return []

    current_user_skills = {skill.skill_id for skill in current_user.skills}

    # Get all users except current user with their skills
    stmt = (
        select(User).options(selectinload(User.skills)).where(User.user_id != user_id)
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


# @router.get("/recommendations", response_model=dict)
# async def get_job_recommendations(
#     current_user: User = Depends(get_current_user),
#     session: AsyncSession = Depends(get_session),
#     top_n: int = Query(
#         10,
#         ge=1,
#         le=50,
#         description="Number of jobs to recommend"
#     )
# ):
#     """
#     Get job recommendations and similar users for the current user.
#     Returns separate lists of recommended jobs and similar users with their skills.
#     """
#     recommendations = await recommend_jobs_for_user(
#         current_user.user_id,
#         session,
#         top_n
#     )

#     # Get current user's skills
#     user_skills = {skill.skill_id for skill in current_user.skills}

#     # Process recommended jobs
#     recommended_jobs = []
#     for job, score, _ in recommendations:
#         # Find matching and missing skills
#         matching_skills = [
#             skill for skill in job.required_skills
#             if skill.skill_id in user_skills
#         ]
#         missing_skills = [
#             skill for skill in job.required_skills
#             if skill.skill_id not in user_skills
#         ]

#         job_data = {
#             "job_id": job.position_id,
#             "job_title": job.job_title,
#             "match_score": round(score * 100, 2),
#             "skills": {
#                 "matching": [
#                     {
#                         "skill_id": skill.skill_id,
#                         "skill_name": skill.skill_name
#                     }
#                     for skill in matching_skills
#                 ],
#                 "missing": [
#                     {
#                         "skill_id": skill.skill_id,
#                         "skill_name": skill.skill_name
#                     }
#                     for skill in missing_skills
#                 ]
#             }
#         }
#         recommended_jobs.append(job_data)

#     # Get similar users
#     similar_users = await find_similar_users(
#         current_user.user_id,
#         session,
#         top_n
#     )

#     # Process similar users
#     recommended_users = []
#     for user, score in similar_users:
#         # Find matching and additional skills
#         matching_skills = [
#             skill for skill in user.skills
#             if skill.skill_id in user_skills
#         ]
#         additional_skills = [
#             skill for skill in user.skills
#             if skill.skill_id not in user_skills
#         ]

#         user_data = {
#             "user_id": user.user_id,
#             "username": user.username,
#             "job_title": user.job_title,
#             "similarity_score": round(score * 100, 2),
#             "skills": {
#                 "matching": [
#                     {
#                         "skill_id": skill.skill_id,
#                         "skill_name": skill.skill_name
#                     }
#                     for skill in matching_skills
#                 ],
#                 "additional": [
#                     {
#                         "skill_id": skill.skill_id,
#                         "skill_name": skill.skill_name
#                     }
#                     for skill in additional_skills
#                 ]
#             }
#         }
#         recommended_users.append(user_data)

#     return {
#         "recommended_jobs": recommended_jobs,
#         "recommended_users": recommended_users
#     }


@router.get("/top-recommendation", response_model=dict)
async def get_top_job_recommendation(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get the top 1 job recommendation based on log likelihood score.
    Returns the best matching job position with log likelihood score and recommended skills.
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

    user_skills = [skill.skill_id for skill in user.skills]

    print(f"\nUser Info:")
    print(f"User ID: {user.user_id}")
    print(f"Username: {user.username}")
    print(f"Job Title: {user.job_title}")
    print(f"User Skills: {user_skills}")

    job_title_variations = []

    # check  job title user has similarity with job title in job_positions
    for job_title, variations in JOB_TITLE_VARIATIONS.items():
        for variation in variations:
            if variation in user.job_title:
                print(f"Job title: {user.job_title} has similarity with {variation} with job title: {job_title}")
                job_title_variations.append(variations)
                break

    print(f"\nJob title variations: {job_title_variations}")

    # Get all jobs with required skills
    query = (
        select(JobPosition)
        .options(selectinload(JobPosition.required_skills))
        .where(
            or_(
                *[
                    JobPosition.job_title.ilike(f"%{variation}%")
                    for variations in job_title_variations
                    for variation in variations
                ]
            )
        )
    )
    result = await session.execute(query)
    jobs = result.scalars().all()

    print(f"\nFound {len(jobs)} total jobs")
    for job in jobs:
        print(f"Found job: {job.job_title}")

    # Calculate log likelihood for each job
    max_ll_value = float("-inf")
    best_job = None
    best_job_skills = None

    print("\nCalculating Log Likelihood Scores:")
    for job in jobs:
        job_skills = [skill.skill_id for skill in job.required_skills]
        ll_value = log_likelihood(user_skills, job_skills)

        print(f"\nJob: {job.job_title}")
        print(f"Required Skills: {job_skills}")
        print(f"Log Likelihood Score: {ll_value:.4f}")

        if ll_value > max_ll_value:
            max_ll_value = ll_value
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

    print(f"\nBest Matching Job:")
    print(f"Title: {best_job.job_title}")
    print(f"Log Likelihood Score: {max_ll_value:.4f}")
    print(f"Required Skills: {best_job_skills}")

    # Get recommended skills
    recommended_skill_ids = recommend_skills(user_skills, best_job_skills)
    print(f"\nRecommended Skills (IDs): {recommended_skill_ids}")

    # Get skill details for recommended skills
    if recommended_skill_ids:
        query = select(Skill).where(Skill.skill_id.in_(recommended_skill_ids))
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
        skill for skill in best_job.required_skills if skill.skill_id in user_skills
    ]

    print("\nMatching Skills:")
    for skill in matching_skills:
        print(f"- {skill.skill_name} (ID: {skill.skill_id})")

    print("\n=== End of Job Recommendation Process ===\n")

    return {
        "job": {
            "position_id": best_job.position_id,
            "job_title": best_job.job_title,
            "log_likelihood": round(max_ll_value, 4),
            "skills": {
                "matching": [
                    {"skill_id": skill.skill_id, "skill_name": skill.skill_name}
                    for skill in matching_skills
                ],
                "recommended": [
                    {"skill_id": skill.skill_id, "skill_name": skill.skill_name}
                    for skill in recommended_skills
                ],
            },
        }
    }
