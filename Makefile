.PHONY: help build up down logs shell clean migrate test

# Default target
help:
	@echo "Available commands:"
	@echo "  build    - Build Docker images"
	@echo "  up       - Start all services"
	@echo "  down     - Stop all services"
	@echo "  logs     - Show logs from all services"
	@echo "  shell    - Open shell in API container"
	@echo "  clean    - Remove containers, networks, and volumes"
	@echo "  migrate  - Run database migrations"
	@echo "  test     - Run tests"

# Build Docker images
build:
	docker-compose -f docker-compose.dev.yml up -d --build

# Start all services
up:
	docker-compose -f docker-compose.dev.yml up -d

# Start all services with logs
up-logs:
	docker-compose -f docker-compose.dev.yml up

# Stop all services
down:
	docker-compose -f docker-compose.dev.yml down

# Show logs from all services
logs:
	docker-compose -f docker-compose.dev.yml logs -f

# Show logs from specific service
logs-api:
	docker-compose -f docker-compose.dev.yml logs -f api

logs-db:
	docker-compose -f docker-compose.dev.yml logs -f postgres

# Open shell in API container
shell:
	docker-compose -f docker-compose.dev.yml exec api bash

# Open shell in database container
shell-db:
	docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d skill_recommender_dev

# Remove containers, networks, and volumes
clean:
	docker-compose -f docker-compose.dev.yml down -v --remove-orphans
	docker system prune -f

# Run database migrations
migrate:
	docker-compose -f docker-compose.dev.yml exec api alembic upgrade head

# Create new migration
migrate-create:
	docker-compose -f docker-compose.dev.yml exec api alembic revision --autogenerate -m "$(message)"

# Run tests
test:
	docker-compose -f docker-compose.dev.yml exec api python -m pytest

# Restart services
restart:
	docker-compose -f docker-compose.dev.yml restart

# Check service status
status:
	docker-compose -f docker-compose.dev.yml ps

# Access pgAdmin
pgadmin:
	@echo "pgAdmin is available at: http://localhost:5050"
	@echo "Email: admin@skillrecommender.com"
	@echo "Password: admin123"

# Access API documentation
docs:
	@echo "API documentation is available at: http://localhost:8001/docs"
	@echo "ReDoc documentation is available at: http://localhost:8001/redoc" 