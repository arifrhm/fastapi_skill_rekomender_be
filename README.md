# FastAPI Skill Recommender

A FastAPI application for skill recommendations using Tortoise ORM with PostgreSQL and Polars.

## Features

- Bearer token authentication with password
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
# Application settings
VERSION=1

# Database settings
DB_USER=your_postgres_user
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=skill_recommender

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

### Authentication
- POST `/api/v1/users/register` - Register a new user
  ```json
  {
    "username": "user1",
    "email": "user1@example.com",
    "password": "your_password",
    "job_title": "Developer"
  }
  ```
  Response:
  ```json
  {
    "user_id": 1,
    "username": "user1",
    "email": "user1@example.com",
    "job_title": "Developer"
  }
  ```

- POST `/api/v1/users/token` - Get Bearer token for authentication
  ```json
  {
    "email": "user1@example.com",
    "password": "your_password"
  }
  ```
  Response:
  ```json
  {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer"
  }
  ```

### User Management
- GET `/api/v1/users/me` - Get current user profile (requires Bearer token)
  Response:
  ```json
  {
    "user_id": 1,
    "username": "user1",
    "email": "user1@example.com",
    "job_title": "Developer"
  }
  ```

### Skill Management
- GET `/api/v1/skills` - List all skills (requires Bearer token)
- POST `/api/v1/skills` - Create a new skill (requires Bearer token)
- POST `/api/v1/skills/user/{skill_id}` - Add skill to user (requires Bearer token)
- DELETE `/api/v1/skills/user/{skill_id}` - Remove skill from user (requires Bearer token)

### Job Position Management
- GET `/api/v1/jobs` - List all job positions (requires Bearer token)
- POST `/api/v1/jobs` - Create a new job position (requires Bearer token)
- GET `/api/v1/jobs/recommendations` - Get job recommendations based on user skills (requires Bearer token)

## Authentication

The API uses Bearer token authentication with password verification. To access protected endpoints:

1. Register a new user using the `/api/v1/users/register` endpoint with your email and password
2. Get a Bearer token using the `/api/v1/users/token` endpoint with your email and password
3. Include the token in the Authorization header for subsequent requests:
```
Authorization: Bearer <your_token>
```

## Database Schema

The application uses the following tables:
- `users_trial` - User information (including hashed passwords)
- `skills_trial` - Available skills
- `users_skills_trial` - User-skill relationships
- `job_positions_trial` - Job positions
- `position_skills_trial` - Job position-skill relationships 