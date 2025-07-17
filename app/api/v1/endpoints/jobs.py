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
    cosine_similarity,
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


class CombinedJobScore(BaseModel):
    job_id: int
    title: str
    skills: List[str]
    cosine_score: float
    llr_score: float
    combined_score: float


class CombinedRecommendationResponse(BaseModel):
    cosine_recommendations: List[CombinedJobScore]
    llr_recommendations: List[CombinedJobScore]
    combined_recommendations: List[CombinedJobScore]
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


@router.get(
    "/combined-recommendation",
    summary="Get job recommendations using both cosine similarity and LLS"
)
async def get_combined_job_recommendation(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get job recommendations using both cosine similarity and LLS algorithms.
    Returns separate recommendations from each method and a combined ranking.
    """
    # Get user skills
    query = (
        select(User)
        .options(selectinload(User.skills))
        .where(User.user_id == current_user.user_id)
    )
    result = await session.execute(query)
    user = result.scalar_one()
    user_skills = [skill.skill_name for skill in user.skills]

    # Get all skills for universe
    all_skills_query = select(distinct(Skill.skill_name))
    all_skills_result = await session.execute(all_skills_query)
    all_skills = [skill[0] for skill in all_skills_result.fetchall()]

    # Get all jobs
    jobs_query = select(Job).options(selectinload(Job.required_skills))
    result = await session.execute(jobs_query)
    jobs = result.scalars().all()

    # Separate calculations for each algorithm
    cosine_job_scores = []
    llr_job_scores = []

    for job in jobs:
        job_skills = [skill.skill_name for skill in job.required_skills]
        
        # Calculate cosine similarity
        cosine_score = cosine_similarity(user_skills, job_skills, all_skills)
        
        # Calculate LLS similarity
        llr_score = llr_similarity(user_skills, job_skills, all_skills)
        
        # Add to respective lists
        cosine_job_scores.append({
            "job_id": job.job_id,
            "title": job.job_title,
            "skills": job_skills,
            "cosine_score": round(cosine_score, 4),
            "algorithm": "cosine_similarity"
        })
        
        llr_job_scores.append({
            "job_id": job.job_id,
            "title": job.job_title,
            "skills": job_skills,
            "llr_score": round(llr_score, 4),
            "algorithm": "llr_similarity"
        })

    # Sort by respective scores
    cosine_recommendations = sorted(
        cosine_job_scores, 
        key=lambda x: x["cosine_score"], 
        reverse=True
    )[:10]
    
    llr_recommendations = sorted(
        llr_job_scores, 
        key=lambda x: x["llr_score"], 
        reverse=True
    )[:10]

    # Create combined recommendations with both scores
    combined_job_scores = []
    for job in jobs:
        job_skills = [skill.skill_name for skill in job.required_skills]
        
        cosine_score = cosine_similarity(user_skills, job_skills, all_skills)
        llr_score = llr_similarity(user_skills, job_skills, all_skills)
        
        # Calculate combined score (weighted average)
        cosine_weight = 0.6
        llr_weight = 0.4
        combined_score = (
            cosine_score * cosine_weight
        ) + (llr_score * llr_weight)
        
        combined_job_scores.append({
            "job_id": job.job_id,
            "title": job.job_title,
            "skills": job_skills,
            "cosine_score": round(cosine_score, 4),
            "llr_score": round(llr_score, 4),
            "combined_score": round(combined_score, 4),
            "algorithm": "combined"
        })

    combined_recommendations = sorted(
        combined_job_scores, 
        key=lambda x: x["combined_score"], 
        reverse=True
    )[:10]

    recommendation_result = {
        "cosine_similarity_recommendations": {
            "algorithm": "cosine_similarity",
            "description": (
                "Recommendations based on vector similarity between "
                "user skills and job requirements"
            ),
            "top_recommendation": (
                cosine_recommendations[0] if cosine_recommendations else None
            ),
            "all_recommendations": cosine_recommendations,
            "total_jobs_analyzed": len(cosine_job_scores)
        },
        "llr_similarity_recommendations": {
            "algorithm": "llr_similarity", 
            "description": (
                "Recommendations based on Log Likelihood Ratio "
                "statistical association"
            ),
            "top_recommendation": (
                llr_recommendations[0] if llr_recommendations else None
            ),
            "all_recommendations": llr_recommendations,
            "total_jobs_analyzed": len(llr_job_scores)
        },
        "combined_recommendations": {
            "algorithm": "combined",
            "description": (
                "Weighted combination of cosine similarity (60%) "
                "and LLS (40%)"
            ),
            "top_recommendation": (
                combined_recommendations[0] if combined_recommendations else None
            ),
            "all_recommendations": combined_recommendations,
            "total_jobs_analyzed": len(combined_job_scores)
        },
        "user_skills": user_skills,
        "summary": {
            "total_jobs_available": len(jobs),
            "user_skill_count": len(user_skills),
            "recommendation_date": (
                datetime.now().isoformat()
            )
        }
    }

    # Audit the recommendation
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


@router.get(
    "/cosine-recommendation",
    summary="Get job recommendations using cosine similarity only"
)
async def get_cosine_recommendation(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get job recommendations using only cosine similarity algorithm.
    """
    # Get user skills
    query = (
        select(User)
        .options(selectinload(User.skills))
        .where(User.user_id == current_user.user_id)
    )
    result = await session.execute(query)
    user = result.scalar_one()
    user_skills = [skill.skill_name for skill in user.skills]

    # Get all skills for universe
    all_skills_query = select(distinct(Skill.skill_name))
    all_skills_result = await session.execute(all_skills_query)
    all_skills = [skill[0] for skill in all_skills_result.fetchall()]

    # Get all jobs
    jobs_query = select(Job).options(selectinload(Job.required_skills))
    result = await session.execute(jobs_query)
    jobs = result.scalars().all()

    job_scores = []

    for job in jobs:
        job_skills = [skill.skill_name for skill in job.required_skills]
        cosine_score = cosine_similarity(user_skills, job_skills, all_skills)
        
        job_scores.append({
            "job_id": job.job_id,
            "title": job.job_title,
            "skills": job_skills,
            "cosine_score": round(cosine_score, 4),
            "algorithm": "cosine_similarity"
        })

    # Sort by cosine score
    recommendations = sorted(
        job_scores, 
        key=lambda x: x["cosine_score"], 
        reverse=True
    )[:10]

    result_data = {
        "algorithm": "cosine_similarity",
        "description": (
            "Recommendations based on vector similarity between "
            "user skills and job requirements"
        ),
        "top_recommendation": recommendations[0] if recommendations else None,
        "all_recommendations": recommendations,
        "user_skills": user_skills,
        "total_jobs_analyzed": len(job_scores),
        "recommendation_date": datetime.now().isoformat()
    }

    # Audit the recommendation
    client_host = request.client.host if request.client else "unknown"
    audit_entry = AuditHistory(
        user_id=current_user.user_id,
        ip_address=client_host,
        recommendation_result=json.dumps(result_data),
        created_at=datetime.now().isoformat()
    )
    session.add(audit_entry)
    await session.commit()

    return result_data


@router.get(
    "/llr-recommendation",
    summary="Get job recommendations using LLS (Log Likelihood Ratio) only"
)
async def get_llr_recommendation(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get job recommendations using only LLS (Log Likelihood Ratio) algorithm.
    """
    # Get user skills
    query = (
        select(User)
        .options(selectinload(User.skills))
        .where(User.user_id == current_user.user_id)
    )
    result = await session.execute(query)
    user = result.scalar_one()
    user_skills = [skill.skill_name for skill in user.skills]

    # Get all skills for universe
    all_skills_query = select(distinct(Skill.skill_name))
    all_skills_result = await session.execute(all_skills_query)
    all_skills = [skill[0] for skill in all_skills_result.fetchall()]

    # Get all jobs
    jobs_query = select(Job).options(selectinload(Job.required_skills))
    result = await session.execute(jobs_query)
    jobs = result.scalars().all()

    job_scores = []

    for job in jobs:
        job_skills = [skill.skill_name for skill in job.required_skills]
        llr_score = llr_similarity(user_skills, job_skills, all_skills)
        
        job_scores.append({
            "job_id": job.job_id,
            "title": job.job_title,
            "skills": job_skills,
            "llr_score": round(llr_score, 4),
            "algorithm": "llr_similarity"
        })

    # Sort by LLS score
    recommendations = sorted(
        job_scores, 
        key=lambda x: x["llr_score"], 
        reverse=True
    )[:10]

    result_data = {
        "algorithm": "llr_similarity",
        "description": (
            "Recommendations based on Log Likelihood Ratio "
            "statistical association"
        ),
        "top_recommendation": recommendations[0] if recommendations else None,
        "all_recommendations": recommendations,
        "user_skills": user_skills,
        "total_jobs_analyzed": len(job_scores),
        "recommendation_date": datetime.now().isoformat()
    }

    # Audit the recommendation
    client_host = request.client.host if request.client else "unknown"
    audit_entry = AuditHistory(
        user_id=current_user.user_id,
        ip_address=client_host,
        recommendation_result=json.dumps(result_data),
        created_at=datetime.now().isoformat()
    )
    session.add(audit_entry)
    await session.commit()

    return result_data


@router.get(
    "/job/{job_id}/skills-analysis",
    summary="Get detailed skills analysis for a specific job"
)
async def get_job_skills_analysis(
    job_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get detailed skills analysis for a specific job including matching skills,
    recommended skills, and similarity scores.
    """
    # Get user skills
    user_query = (
        select(User)
        .options(selectinload(User.skills))
        .where(User.user_id == current_user.user_id)
    )
    user_result = await session.execute(user_query)
    user = user_result.scalar_one()
    user_skills = [skill.skill_name for skill in user.skills]

    # Get job with skills
    job_query = (
        select(Job)
        .options(selectinload(Job.required_skills))
        .where(Job.job_id == job_id)
    )
    job_result = await session.execute(job_query)
    job = job_result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    job_skills = [skill.skill_name for skill in job.required_skills]

    # Get all skills for universe
    all_skills_query = select(distinct(Skill.skill_name))
    all_skills_result = await session.execute(all_skills_query)
    all_skills = [skill[0] for skill in all_skills_result.fetchall()]

    # Calculate similarity scores
    cosine_score = cosine_similarity(user_skills, job_skills, all_skills)
    llr_score = llr_similarity(user_skills, job_skills, all_skills)

    # Get matching skills
    matching_skill_names = set(user_skills) & set(job_skills)
    matching_skills_query = (
        select(Skill)
        .where(Skill.skill_name.in_(matching_skill_names))
    )
    matching_skills_result = await session.execute(matching_skills_query)
    matching_skills = matching_skills_result.scalars().all()

    # Get recommended skills
    recommended_skill_names = recommend_skills(user_skills, job_skills)
    recommended_skills_query = (
        select(Skill)
        .where(Skill.skill_name.in_(recommended_skill_names))
    )
    recommended_skills_result = await session.execute(recommended_skills_query)
    recommended_skills = recommended_skills_result.scalars().all()

    # Get missing skills (skills user has but job doesn't need)
    missing_skill_names = set(user_skills) - set(job_skills)
    missing_skills_query = (
        select(Skill)
        .where(Skill.skill_name.in_(missing_skill_names))
    )
    missing_skills_result = await session.execute(missing_skills_query)
    missing_skills = missing_skills_result.scalars().all()

    analysis_result = {
        "job": {
            "job_id": job.job_id,
            "job_title": job.job_title,
            "description": job.description,
        },
        "similarity_scores": {
            "cosine_similarity": round(cosine_score, 4),
            "llr_similarity": round(llr_score, 4),
        },
        "skills_analysis": {
            "matching_skills": [
                {"skill_id": skill.skill_id, "skill_name": skill.skill_name}
                for skill in matching_skills
            ],
            "recommended_skills": [
                {"skill_id": skill.skill_id, "skill_name": skill.skill_name}
                for skill in recommended_skills
            ],
            "missing_skills": [
                {"skill_id": skill.skill_id, "skill_name": skill.skill_name}
                for skill in missing_skills
            ],
        },
        "user_skills": user_skills,
        "job_required_skills": job_skills,
        "stats": {
            "total_user_skills": len(user_skills),
            "total_job_skills": len(job_skills),
            "matching_count": len(matching_skills),
            "recommended_count": len(recommended_skills),
            "missing_count": len(missing_skills),
            "match_percentage": round(
                (len(matching_skills) / len(job_skills)) * 100, 2
            ) if job_skills else 0,
        },
    }

    # Audit the analysis
    client_host = request.client.host if request.client else "unknown"
    audit_entry = AuditHistory(
        user_id=current_user.user_id,
        ip_address=client_host,
        recommendation_result=json.dumps(analysis_result),
        created_at=datetime.now().isoformat()
    )
    session.add(audit_entry)
    await session.commit()

    return analysis_result
