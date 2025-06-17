from fastapi import APIRouter
from app.api.v1.endpoints import users, skills, jobs, audit, roles

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(skills.router, prefix="/skills", tags=["skills"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"]) 