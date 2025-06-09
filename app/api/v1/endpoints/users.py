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
    user_skills
)
from app.core.config import settings
from app.database import get_session

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
    
    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=UserResponse)
async def register_user(
    user: UserCreate,
    session: AsyncSession = Depends(get_session)
):
    # Check if user already exists
    query = select(User).where(User.email == user.email)
    result = await session.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user with hashed password
    user_dict = user.dict()
    skill_ids = user_dict.pop("skill_ids", [])
    hashed_password = get_password_hash(user_dict.pop("password"))

    # Create user
    user_obj = User(
        **user_dict,
        hashed_password=hashed_password
    )
    session.add(user_obj)
    await session.commit()
    await session.refresh(user_obj)

    # Add skills if provided
    if skill_ids:
        # Verify all skills exist
        query = select(Skill).where(Skill.skill_id.in_(skill_ids))
        result = await session.execute(query)
        skills = result.scalars().all()
        
        if len(skills) != len(skill_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more skills not found"
            )

        # Add skills to user using the association table directly
        for skill in skills:
            stmt = user_skills.insert().values(
                user_id=user_obj.user_id,
                skill_id=skill.skill_id
            )
            await session.execute(stmt)
        await session.commit()

    # Reload user with skills using selectinload
    query = (
        select(User)
        .options(selectinload(User.skills))
        .where(User.user_id == user_obj.user_id)
    )
    result = await session.execute(query)
    user_with_skills = result.scalar_one()
    
    return user_with_skills


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
async def read_users_me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # Reload user with skills
    query = select(User).options(selectinload(User.skills)).where(User.user_id == current_user.user_id)
    result = await session.execute(query)
    user = result.scalar_one()
    return user


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
