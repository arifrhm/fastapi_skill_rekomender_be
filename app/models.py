from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator


class User(models.Model):
    user_id = fields.IntField(pk=True)
    username = fields.CharField(max_length=255, unique=True)
    email = fields.CharField(max_length=255, unique=True)
    hashed_password = fields.CharField(max_length=255)
    job_title = fields.CharField(max_length=100)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users_trial"


class Skill(models.Model):
    skill_id = fields.IntField(pk=True)
    skill_name = fields.CharField(max_length=255, unique=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "skills_trial"


class UserSkill(models.Model):
    user_skill_id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="user_skills")
    skill = fields.ForeignKeyField("models.Skill", related_name="user_skills")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users_skills_trial"


class JobPosition(models.Model):
    position_id = fields.IntField(pk=True)
    job_title = fields.CharField(max_length=255, unique=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    required_skills = fields.ManyToManyField(
        "models.Skill", through="position_skills_trial", related_name="job_positions"
    )

    class Meta:
        table = "job_positions_trial"


class PositionSkill(models.Model):
    position_skill_id = fields.IntField(pk=True)
    position = fields.ForeignKeyField(
        "models.JobPosition", related_name="position_skills"
    )
    skill = fields.ForeignKeyField("models.Skill", related_name="position_skills")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "position_skills_trial"


# Pydantic models for API
User_Pydantic = pydantic_model_creator(User, name="User", exclude=("hashed_password",))
UserIn_Pydantic = pydantic_model_creator(User, name="UserIn", exclude_readonly=True)
Skill_Pydantic = pydantic_model_creator(Skill, name="Skill")
JobPosition_Pydantic = pydantic_model_creator(JobPosition, name="JobPosition")
