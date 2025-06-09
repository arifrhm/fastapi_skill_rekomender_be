from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.models import Skill, User, UserSkill, Skill_Pydantic
from app.api.v1.endpoints.users import get_current_user

router = APIRouter()


@router.get("/", response_model=List[Skill_Pydantic])
async def get_skills():
    return await Skill_Pydantic.from_queryset(Skill.all())


@router.post("/", response_model=Skill_Pydantic)
async def create_skill(skill_name: str):
    skill = await Skill.get_or_none(skill_name=skill_name)
    if skill:
        return await Skill_Pydantic.from_tortoise_orm(skill)

    skill = await Skill.create(skill_name=skill_name)
    return await Skill_Pydantic.from_tortoise_orm(skill)


@router.post("/user/{skill_id}")
async def add_user_skill(skill_id: int, current_user: User = Depends(get_current_user)):
    skill = await Skill.get_or_none(skill_id=skill_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found"
        )

    # Check if user already has this skill
    if await UserSkill.exists(user=current_user, skill=skill):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has this skill",
        )

    await UserSkill.create(user=current_user, skill=skill)
    return {"message": "Skill added successfully"}


@router.delete("/user/{skill_id}")
async def remove_user_skill(
    skill_id: int, current_user: User = Depends(get_current_user)
):
    skill = await Skill.get_or_none(skill_id=skill_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found"
        )

    user_skill = await UserSkill.get_or_none(user=current_user, skill=skill)
    if not user_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not have this skill",
        )

    await user_skill.delete()
    return {"message": "Skill removed successfully"}
