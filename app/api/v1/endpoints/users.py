from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    User,
    UserCreate,
    UserLogin,
    UserResponse,
    Role,
    user_roles,
    Skill,
    user_skills
)
from app.core.config import settings
from app.database import get_session
from app.core.auth import (
    get_current_user,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_password
)

router = APIRouter()
security = HTTPBearer()

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session)
):
    # Check if email already exists
    query = select(User).where(User.email == user_data.email)
    result = await session.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username already exists
    query = select(User).where(User.username == user_data.username)
    result = await session.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Get USER role
    query = select(Role).where(Role.role_name == "USER")
    result = await session.execute(query)
    user_role = result.scalar_one_or_none()
    
    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default USER role not found"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        job_title=user_data.job_title
    )
    
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    
    # Add USER role to user
    await session.execute(
        insert(user_roles).values(
            user_id=new_user.user_id,
            role_id=user_role.role_id
        )
    )
    await session.commit()

    # Add skills if provided
    if user_data.skill_ids:
        # Verify all skills exist
        query = select(Skill).where(Skill.skill_id.in_(user_data.skill_ids))
        result = await session.execute(query)
        skills = result.scalars().all()
        
        if len(skills) != len(user_data.skill_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more skills not found"
            )

        # Add skills to user using the association table directly
        for skill in skills:
            await session.execute(
                insert(user_skills).values(
                    user_id=new_user.user_id,
                    skill_id=skill.skill_id
                )
            )
        await session.commit()
    
    # Reload user with relationships
    query = (
        select(User)
        .options(selectinload(User.roles), selectinload(User.skills))
        .where(User.user_id == new_user.user_id)
    )
    result = await session.execute(query)
    user_with_relationships = result.scalar_one()
    
    # Create response with first role
    user_dict = {
        "user_id": user_with_relationships.user_id,
        "username": user_with_relationships.username,
        "email": user_with_relationships.email,
        "job_title": user_with_relationships.job_title,
        "skills": user_with_relationships.skills,
        "role": user_with_relationships.roles[0] if user_with_relationships.roles else None
    }
    
    return UserResponse.model_validate(user_dict)


@router.post("/login")
async def get_token(
    user: UserLogin,
    session: AsyncSession = Depends(get_session)
):
    query = select(User).where(User.email == user.email)
    result = await session.execute(query)
    db_user = result.scalar_one_or_none()
    
    if not db_user or not verify_password(
        user.password,
        db_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens with string user_id
    user_id_str = str(db_user.user_id)
    access_token = create_access_token(data={"sub": user_id_str})
    refresh_token = create_refresh_token(data={"sub": user_id_str})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get current user information with first role and skills
    """
    # Reload user with relationships
    query = (
        select(User)
        .options(selectinload(User.roles), selectinload(User.skills))
        .where(User.user_id == current_user.user_id)
    )
    result = await session.execute(query)
    user = result.scalar_one()
    
    # Create response with first role
    user_dict = {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "job_title": user.job_title,
        "skills": user.skills,
        "role": user.roles[0] if user.roles else None
    }
    
    return UserResponse.model_validate(user_dict)


@router.post("/refresh")
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
):
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_sub": False}  # Disable subject validation
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # Convert to integer regardless of input type
        user_id = int(str(user_id))
    except (JWTError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify user still exists
    query = select(User).where(User.user_id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create new tokens
    user_id_str = str(user.user_id)
    access_token = create_access_token(data={"sub": user_id_str})
    refresh_token = create_refresh_token(data={"sub": user_id_str})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
