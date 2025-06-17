from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime

from app.database import get_session
from app.models import AuditHistory, AuditHistoryResponse, User
from app.core.auth import get_admin_user

router = APIRouter()

@router.get("/audit-history", response_model=List[AuditHistoryResponse])
async def get_audit_history(
    current_user: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Get all audit history (admin only)
    """
    query = (
        select(AuditHistory)
        .order_by(AuditHistory.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    result = await session.execute(query)
    audit_history = result.scalars().all()
    
    # Get usernames for all entries
    response = []
    for audit in audit_history:
        user_query = select(User).where(User.user_id == audit.user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if user:
            response.append(AuditHistoryResponse(
                id=audit.id,
                user_id=audit.user_id,
                ip_address=audit.ip_address,
                recommendation_result=audit.recommendation_result,
                created_at=audit.created_at,
                username=user.username
            ))
    
    return response

@router.get("/audit-history/admin", response_model=List[AuditHistoryResponse])
async def get_all_audit_history(
    current_user: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Get all audit history (admin only)
    """
    query = (
        select(AuditHistory)
        .order_by(AuditHistory.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    result = await session.execute(query)
    audit_history = result.scalars().all()
    
    # Get usernames for all entries
    response = []
    for audit in audit_history:
        user_query = select(User).where(User.user_id == audit.user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if user:
            response.append(AuditHistoryResponse(
                id=audit.id,
                user_id=audit.user_id,
                ip_address=audit.ip_address,
                recommendation_result=audit.recommendation_result,
                created_at=audit.created_at,
                username=user.username
            ))
    
    return response 