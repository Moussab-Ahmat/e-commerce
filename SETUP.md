# Django 5 Project Scaffold Setup

## Quick Start

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Start services with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser (optional):**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run server:**
   ```bash
   python manage.py runserver
   ```

7. **Test health endpoint:**
   ```bash
   curl http://localhost:8000/health/
   ```

8. **Run tests:**
   ```bash
   pytest
   ```

## File Structure

```
.
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py      # Environment-based settings loader
│   │   ├── base.py          # Base settings
│   │   ├── development.py  # Development settings
│   │   └── production.py   # Production settings
│   ├── urls.py              # URL configuration
│   ├── views.py             # Health check view
│   └── wsgi.py              # WSGI config
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   └── test_health.py       # Health endpoint tests
├── docker-compose.yml        # Postgres + Redis
├── .env.example             # Environment variables template
├── pytest.ini               # Pytest configuration
├── requirements.txt         # Python dependencies
└── manage.py                # Django management script
```

## Environment Variables (.env.example)

```env
# Environment
ENVIRONMENT=development

# Django Settings
SECRET_KEY=django-insecure-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000

# Logging
LOG_LEVEL=INFO
DJANGO_LOG_LEVEL=INFO

# Production Security (set to True in production)
SECURE_SSL_REDIRECT=False
```

## Acceptance Criteria

✅ **Pytest runs:** `pytest` executes successfully  
✅ **Server starts:** `python manage.py runserver` starts without errors  
✅ **/health/ returns 200 JSON:** `GET /health/` returns `{"status": "ok", "service": "django"}`

## Features

- ✅ Django 5.0
- ✅ DRF configured
- ✅ SimpleJWT authentication
- ✅ CORS headers
- ✅ Environment-based configuration
- ✅ Logging configured
- ✅ Docker Compose (Postgres + Redis)
- ✅ Pytest setup with coverage
- ✅ Health check endpoint

