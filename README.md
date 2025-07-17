# FastAPI Skill Recommender Backend

A FastAPI-based backend service for job skill recommendations using multiple similarity algorithms.

## Features

- User authentication and authorization
- Job and skill management
- Multiple recommendation algorithms:
  - Cosine Similarity
  - Log Likelihood Ratio (LLR)
  - Combined recommendations
- Detailed skills analysis
- Audit logging

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration

### Jobs
- `GET /api/v1/jobs/` - Get all jobs with pagination
- `GET /api/v1/jobs/top-recommendation` - Get top job recommendation using cosine similarity
- `GET /api/v1/jobs/cosine-recommendation` - Get recommendations using cosine similarity only
- `GET /api/v1/jobs/llr-recommendation` - Get recommendations using LLS (Log Likelihood Ratio) only
- `GET /api/v1/jobs/combined-recommendation` - Get recommendations using both cosine similarity and LLS
- `GET /api/v1/jobs/job/{job_id}/skills-analysis` - Get detailed skills analysis for a specific job

### Skills
- `GET /api/v1/skills/` - Get all skills
- `POST /api/v1/skills/` - Create new skill

### Users
- `GET /api/v1/users/me` - Get current user profile
- `PUT /api/v1/users/me` - Update user profile

## Recommendation Algorithms

### 1. Cosine Similarity
- Measures similarity between user skills and job requirements
- Uses vector representation of skills
- Range: 0 to 1 (higher is better)

### 2. Log Likelihood Ratio (LLR)
- Statistical measure of association between skill sets
- Considers the likelihood of skill co-occurrence
- Range: 0 to infinity (higher is better)

### 3. Combined Recommendations
- Weighted combination of both algorithms
- Default weights: Cosine (60%), LLS (40%)
- Provides comprehensive ranking

## Response Format

### Cosine Similarity Recommendation Response
```json
{
  "algorithm": "cosine_similarity",
  "description": "Recommendations based on vector similarity between user skills and job requirements",
  "top_recommendation": {
    "job_id": 1,
    "title": "Backend Developer",
    "skills": ["Python", "FastAPI", "SQL"],
    "cosine_score": 0.85,
    "algorithm": "cosine_similarity"
  },
  "all_recommendations": [...],
  "user_skills": ["Python", "JavaScript"],
  "total_jobs_analyzed": 50,
  "recommendation_date": "2024-01-01T12:00:00"
}
```

### LLS Recommendation Response
```json
{
  "algorithm": "llr_similarity",
  "description": "Recommendations based on Log Likelihood Ratio statistical association",
  "top_recommendation": {
    "job_id": 2,
    "title": "Frontend Developer",
    "skills": ["JavaScript", "React", "CSS"],
    "llr_score": 15.2,
    "algorithm": "llr_similarity"
  },
  "all_recommendations": [...],
  "user_skills": ["Python", "JavaScript"],
  "total_jobs_analyzed": 50,
  "recommendation_date": "2024-01-01T12:00:00"
}
```

### Combined Recommendation Response
```json
{
  "cosine_similarity_recommendations": {
    "algorithm": "cosine_similarity",
    "description": "Recommendations based on vector similarity between user skills and job requirements",
    "top_recommendation": {...},
    "all_recommendations": [...],
    "total_jobs_analyzed": 50
  },
  "llr_similarity_recommendations": {
    "algorithm": "llr_similarity",
    "description": "Recommendations based on Log Likelihood Ratio statistical association",
    "top_recommendation": {...},
    "all_recommendations": [...],
    "total_jobs_analyzed": 50
  },
  "combined_recommendations": {
    "algorithm": "combined",
    "description": "Weighted combination of cosine similarity (60%) and LLS (40%)",
    "top_recommendation": {
      "job_id": 1,
      "title": "Backend Developer",
      "skills": ["Python", "FastAPI", "SQL"],
      "cosine_score": 0.85,
      "llr_score": 12.5,
      "combined_score": 0.71,
      "algorithm": "combined"
    },
    "all_recommendations": [...],
    "total_jobs_analyzed": 50
  },
  "user_skills": ["Python", "JavaScript"],
  "summary": {
    "total_jobs_available": 50,
    "user_skill_count": 2,
    "recommendation_date": "2024-01-01T12:00:00"
  }
}
```

### Skills Analysis Response
```json
{
  "job": {
    "job_id": 1,
    "job_title": "Backend Developer",
    "description": "Job description..."
  },
  "similarity_scores": {
    "cosine_similarity": 0.85,
    "llr_similarity": 12.5
  },
  "skills_analysis": {
    "matching_skills": [...],
    "recommended_skills": [...],
    "missing_skills": [...]
  },
  "stats": {
    "total_user_skills": 5,
    "total_job_skills": 8,
    "matching_count": 3,
    "recommended_count": 5,
    "missing_count": 2,
    "match_percentage": 37.5
  }
}
```

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up database and run migrations
4. Start the server: `uvicorn main:app --reload`

## Docker

Use the provided Docker configuration for containerized deployment:

```bash
docker-compose -f docker-compose.dev.yml up --build
```

## Development

The project includes Docker configuration for development with hot reload and database setup. 