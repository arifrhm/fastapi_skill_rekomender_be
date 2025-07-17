-- Initialize database for Skill Recommender
-- This script runs when the PostgreSQL container starts for the first time

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set timezone
SET timezone = 'UTC';

-- Create additional databases if needed (optional)
-- CREATE DATABASE skill_recommender_test;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE skill_recommender_dev TO postgres;

-- You can add more initialization SQL here if needed
-- For example, creating initial tables or inserting seed data 