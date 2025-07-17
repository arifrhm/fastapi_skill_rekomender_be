# Docker Development Environment

Dokumentasi ini menjelaskan cara menggunakan Docker Compose untuk development environment aplikasi FastAPI Skill Recommender.

## Prerequisites

- Docker
- Docker Compose
- Make (opsional, untuk menggunakan Makefile)

## Struktur File

```
├── Dockerfile                    # Docker image untuk aplikasi
├── docker-compose.dev.yml        # Konfigurasi utama Docker Compose
├── docker-compose.override.yml   # Override untuk development
├── .dockerignore                 # File yang diabaikan saat build
├── init-db.sql                   # Script inisialisasi database
├── Makefile                      # Helper commands
└── README-Docker.md             # Dokumentasi ini
```

## Services

### 1. PostgreSQL Database
- **Image**: `postgres:15-alpine`
- **Port**: `5432`
- **Database**: `skill_recommender_dev`
- **User**: `postgres`
- **Password**: `postgres123`

### 2. FastAPI Application
- **Port**: `8000`
- **Auto-reload**: Enabled
- **Volume mounting**: Enabled untuk development

### 3. pgAdmin (Optional)
- **Port**: `5050`
- **Email**: `admin@skillrecommender.com`
- **Password**: `admin123`

## Quick Start

### Menggunakan Makefile (Recommended)

```bash
# Build images
make build

# Start all services
make up

# View logs
make logs

# Stop services
make down

# Clean up everything
make clean
```

### Menggunakan Docker Compose Langsung

```bash
# Build dan start services
docker-compose -f docker-compose.dev.yml up --build

# Start services in background
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop services
docker-compose -f docker-compose.dev.yml down
```

## Environment Variables

Aplikasi menggunakan environment variables berikut:

```env
VERSION=1.0.0
DB_USER=postgres
DB_PASSWORD=postgres123
DB_HOST=postgres
DB_PORT=5432
DB_NAME=skill_recommender_dev
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

## Useful Commands

### Development

```bash
# Access API container shell
make shell

# Access database shell
make shell-db

# View API logs
make logs-api

# View database logs
make logs-db

# Restart services
make restart

# Check service status
make status
```

### Database Operations

```bash
# Run migrations
make migrate

# Create new migration
make migrate-create message="add new table"

# Access pgAdmin
make pgadmin
```

### Testing

```bash
# Run tests
make test
```

## Access Points

- **API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **ReDoc Documentation**: http://localhost:8001/redoc
- **Health Check**: http://localhost:8001/health
- **pgAdmin**: http://localhost:5050

## Troubleshooting

### Port Already in Use

Jika port sudah digunakan, ubah port di `docker-compose.dev.yml`:

```yaml
ports:
  - "8002:8000"  # Ganti 8001 dengan port lain
```

### Database Connection Issues

1. Pastikan PostgreSQL container sudah running:
   ```bash
   make status
   ```

2. Cek logs database:
   ```bash
   make logs-db
   ```

3. Restart services:
   ```bash
   make restart
   ```

### Permission Issues

Jika ada masalah permission, jalankan:

```bash
sudo chown -R $USER:$USER .
```

### Clean Start

Untuk clean start:

```bash
make clean
make build
make up
```

## Production Considerations

Untuk production, pastikan untuk:

1. Mengubah `SECRET_KEY` dengan key yang aman
2. Menggunakan environment variables yang berbeda
3. Menonaktifkan auto-reload
4. Menggunakan volume yang persistent
5. Mengkonfigurasi backup database
6. Menggunakan reverse proxy (nginx)
7. Mengaktifkan SSL/TLS

## Development Tips

1. **Hot Reload**: File changes akan otomatis reload karena volume mounting
2. **Database Persistence**: Data database disimpan di Docker volume
3. **Logs**: Gunakan `make logs` untuk melihat logs real-time
4. **Shell Access**: Gunakan `make shell` untuk debugging
5. **pgAdmin**: Berguna untuk melihat dan mengelola database secara visual 