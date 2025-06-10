import math
from typing import List, Set, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import User, Skill, JobPosition


def entropy(*counts: int) -> float:
    """Calculate entropy for Log-Likelihood Similarity."""
    total = sum(counts)
    return sum(c * math.log(c / total) for c in counts if c > 0)


def compute_lls(skills1: Set[int], skills2: Set[int], all_skills: Set[int]) -> float:
    """
    Compute Log-Likelihood Similarity between two sets of skills.

    Args:
        skills1: Set of skill IDs for first user/job
        skills2: Set of skill IDs for second user/job
        all_skills: Set of all possible skill IDs

    Returns:
        float: LLS score between the two sets of skills
    """
    k11 = len(skills1 & skills2)  # Both have
    k12 = len(skills2 - skills1)  # Only second has
    k21 = len(skills1 - skills2)  # Only first has
    k22 = len(all_skills - (skills1 | skills2))  # Neither has

    Hk = entropy(k11, k12, k21, k22)
    Hki = entropy(k11 + k12, k21 + k22)
    Hkj = entropy(k11 + k21, k12 + k22)

    return 2 * (Hk - Hki - Hkj)


async def get_all_skills(session: AsyncSession) -> Set[int]:
    """Get all skill IDs from the database."""
    query = select(Skill)
    result = await session.execute(query)
    skills = result.scalars().all()
    return {skill.skill_id for skill in skills}


async def recommend_skills_for_user(
    user_id: int, session: AsyncSession, top_n: int = 5
) -> Tuple[List[Tuple[int, float]], List[int]]:
    """
    Recommend skills for a user based on similar users' skills.

    Args:
        user_id: ID of the target user
        session: Database session
        top_n: Number of similar users to consider

    Returns:
        Tuple containing:
        - List of tuples (user_id, similarity_score) for similar users
        - List of recommended skill IDs
    """
    # Get target user with skills
    query = (
        select(User).options(selectinload(User.skills)).where(User.user_id == user_id)
    )
    result = await session.execute(query)
    target_user = result.scalar_one()
    target_skills = {skill.skill_id for skill in target_user.skills}

    # Get all users with their skills
    query = select(User).options(selectinload(User.skills))
    result = await session.execute(query)
    all_users = result.scalars().all()

    # Get all possible skills
    all_skills = await get_all_skills(session)

    # Calculate LLS scores for similar users
    similar_users = []
    for other_user in all_users:
        if other_user.user_id == user_id:
            continue

        other_skills = {skill.skill_id for skill in other_user.skills}
        overlap = target_skills & other_skills

        if len(overlap) > 0:
            score = compute_lls(target_skills, other_skills, all_skills)
            similar_users.append((other_user.user_id, round(score, 4)))

    # Sort users by LLS score
    similar_users.sort(key=lambda x: -x[1])
    top_similar_users = [u for u, _ in similar_users[:top_n]]

    # Get recommended skills from similar users
    recommended_skills = set()
    for user_id in top_similar_users:
        query = (
            select(User)
            .options(selectinload(User.skills))
            .where(User.user_id == user_id)
        )
        result = await session.execute(query)
        user = result.scalar_one()
        user_skills = {skill.skill_id for skill in user.skills}
        recommended_skills.update(user_skills - target_skills)

    return similar_users[:top_n], list(recommended_skills)


async def find_similar_users(
    user_id: int, session: AsyncSession, top_n: int = 10
) -> List[Tuple[User, float]]:
    """
    Find users with similar job titles and skills using LLS score.

    Args:
        user_id: ID of the target user
        session: Database session
        top_n: Number of similar users to return

    Returns:
        List of tuples (user, similarity_score)
    """
    # Get target user with skills
    query = (
        select(User).options(selectinload(User.skills)).where(User.user_id == user_id)
    )
    result = await session.execute(query)
    target_user = result.scalar_one()
    target_skills = {skill.skill_id for skill in target_user.skills}
    target_job_title = target_user.job_title.lower()

    # Get all users with skills (excluding target user)
    query = (
        select(User).options(selectinload(User.skills)).where(User.user_id != user_id)
    )
    result = await session.execute(query)
    users = result.scalars().all()

    # Get all possible skills
    all_skills = await get_all_skills(session)

    # Calculate similarity scores for each user
    user_scores = []
    for user in users:
        user_skills = {skill.skill_id for skill in user.skills}
        user_job_title = user.job_title.lower()

        # Calculate LLS score for skills
        skill_lls_score = compute_lls(target_skills, user_skills, all_skills)

        # Calculate job title similarity (simple word overlap)
        target_words = set(target_job_title.split())
        user_words = set(user_job_title.split())
        job_title_similarity = (
            len(target_words & user_words) / len(target_words) if target_words else 0
        )

        # Calculate skill match percentage
        matching_skills = len(target_skills & user_skills)
        skill_match_percentage = (
            matching_skills / len(target_skills) * 100 if target_skills else 0
        )

        # Combine scores with weights
        final_score = (
            skill_lls_score * 0.4  # LLS score weight
            + job_title_similarity * 0.3  # Job title similarity weight
            + (skill_match_percentage / 100) * 0.3  # Skill match percentage weight
        )

        user_scores.append((user, final_score))

    # Sort by score and return top N
    user_scores.sort(key=lambda x: -x[1])
    return user_scores[:top_n]


async def recommend_jobs_for_user(
    user_id: int,
    session: AsyncSession,
    top_n: int = 10
) -> List[Tuple[JobPosition, float, List[Tuple[User, float]]]]:
    """
    Recommend jobs for a user based on skill similarity.
    
    Args:
        user_id: ID of the target user
        session: Database session
        top_n: Number of jobs to recommend
    
    Returns:
        List of tuples (job_position, match_percentage, similar_users)
    """
    # Get user with skills
    query = (
        select(User)
        .options(selectinload(User.skills))
        .where(User.user_id == user_id)
    )
    result = await session.execute(query)
    user = result.scalar_one()
    user_skills = {skill.skill_id for skill in user.skills}
    
    # Get similar users
    similar_users = await find_similar_users(user_id, session, top_n)
    
    # Debug information
    print("\n=== Similar Users Debug Info ===")
    for user, score in similar_users:
        print(f"\nUser ID: {user.user_id}")
        print(f"Username: {user.username}")
        print(f"Job Title: {user.job_title}")
        print(f"Similarity Score: {score:.2f}")
        print("Skills:")
        for skill in user.skills:
            print(f"  - {skill.skill_name} (ID: {skill.skill_id})")
    print("\n=============================")
    
    # Get all jobs with required skills
    query = (
        select(JobPosition)
        .options(selectinload(JobPosition.required_skills))
    )
    result = await session.execute(query)
    jobs = result.scalars().all()
    
    # Get all possible skills
    all_skills = await get_all_skills(session)
    
    # Calculate match scores for each job
    job_scores = []
    for job in jobs:
        required_skills = {skill.skill_id for skill in job.required_skills}
        
        # Calculate LLS score
        lls_score = compute_lls(user_skills, required_skills, all_skills)
        
        # Calculate match percentage
        matching_skills = len(user_skills & required_skills)
        match_percentage = (
            matching_skills / len(required_skills) * 100 if required_skills else 0
        )
        
        # Combine scores (you can adjust the weights)
        final_score = (lls_score * 0.3) + (match_percentage * 0.7)
        
        # Get similar users who have this job title
        job_similar_users = [
            (su[0], su[1]) for su in similar_users 
            if su[0].job_title.lower() == job.job_title.lower()
        ]
        
        job_scores.append((job, final_score, job_similar_users))
    
    # Sort by score and return top N
    job_scores.sort(key=lambda x: -x[1])
    return job_scores[:top_n]
