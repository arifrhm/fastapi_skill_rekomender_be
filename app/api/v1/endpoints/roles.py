from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_session
from app.models import Role, RoleCreate, RoleResponse, User
from app.core.auth import get_admin_user

router = APIRouter()

@router.post("/", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new role (admin only)
    """
    # Check if role name already exists
    query = select(Role).where(Role.role_name == role_data.role_name)
    result = await session.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role name already exists"
        )

    # Create new role
    new_role = Role(
        role_name=role_data.role_name,
        description=role_data.description
    )
    session.add(new_role)
    await session.commit()
    await session.refresh(new_role)

    return RoleResponse.model_validate(new_role)

@router.get("/", response_model=List[RoleResponse])
async def get_roles(
    current_user: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get all roles (admin only)
    """
    query = select(Role)
    result = await session.execute(query)
    roles = result.scalars().all()
    return [RoleResponse.model_validate(role) for role in roles]

@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    current_user: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get role by ID (admin only)
    """
    query = select(Role).where(Role.role_id == role_id)
    result = await session.execute(query)
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    return RoleResponse.model_validate(role) 