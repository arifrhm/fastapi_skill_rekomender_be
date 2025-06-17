from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import insert

from app.models import (
    User,
    UserCreate,
    UserLogin,
    UserResponse,
    Skill,
    user_skills,
    UserRole,
    Role
)
from app.core.config import settings
from app.database import get_session
from app.core.auth import get_current_user, get_password_hash, create_access_token

router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    # Ensure subject is string
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    print("Access token payload:", to_encode)  # Debug log
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire})
    # Ensure subject is string
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    print("Refresh token payload:", to_encode)  # Debug log
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        # Convert string user_id back to integer
        user_id = int(user_id)
    except (JWTError, ValueError):
        raise credentials_exception
    
    query = select(User).where(User.user_id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    print("User:", user)
    if user is None:
        raise credentials_exception
    return user


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

    # Verify role exists
    query = select(Role).where(Role.role_id == user_data.role_id)
    result = await session.execute(query)
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role ID"
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
    
    # Add role to user
    await session.execute(
        insert(user_roles).values(
            user_id=new_user.user_id,
            role_id=user_data.role_id
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
        "roles": user_with_relationships.roles[0] if user_with_relationships.roles else None
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
        print("Received token:", token)  # Debug log
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_sub": False}  # Disable subject validation
        )
        print("Decoded payload:", payload)  # Debug log
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
        print("Token error:", str(e))  # Debug log
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify user still exists
    query = select(User).where(User.user_id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create new tokens with string user_id
    user_id_str = str(user_id)
    access_token = create_access_token(data={"sub": user_id_str})
    refresh_token = create_refresh_token(data={"sub": user_id_str})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
