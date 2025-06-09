# FastAPI Skill Recommender

A FastAPI application for skill recommendations using Tortoise ORM with PostgreSQL and Polars.

## Features

- User authentication with JWT tokens
- Skill management
- Job position management
- Skill-based job recommendations
- PostgreSQL database with Tortoise ORM
- Fast data processing with Polars

## Prerequisites

- Python 3.8+
- PostgreSQL 12+

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd fastapi-skill-recommender
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with the following variables:
```env
# Database settings
POSTGRES_USER=your_postgres_user
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=skill_recommender

# JWT settings
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

5. Create the PostgreSQL database:
```bash
createdb skill_recommender
```

## Running the Application

1. Start the FastAPI server:
```bash
uvicorn main:app --reload
```

2. Access the API documentation:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## API Endpoints

### User Management
- POST `/api/v1/users/register` - Register a new user
- POST `/api/v1/users/token` - Login and get access token
- GET `/api/v1/users/me` - Get current user profile

### Skill Management
- GET `/api/v1/skills` - List all skills
- POST `/api/v1/skills` - Create a new skill
- POST `/api/v1/skills/user/{skill_id}` - Add skill to user
- DELETE `/api/v1/skills/user/{skill_id}` - Remove skill from user

### Job Position Management
- GET `/api/v1/jobs` - List all job positions
- POST `/api/v1/jobs` - Create a new job position
- GET `/api/v1/jobs/recommendations` - Get job recommendations based on user skills

## Database Schema

The application uses the following tables:
- `users_trial` - User information
- `skills_trial` - Available skills
- `users_skills_trial` - User-skill relationships
- `job_positions_trial` - Job positions
- `position_skills_trial` - Job position-skill relationships 