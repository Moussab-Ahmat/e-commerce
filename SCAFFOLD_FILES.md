# Django 5 Scaffold - File List

## Exact Files and Paths Created

### Configuration Files
- `config/__init__.py` - Empty init file
- `config/settings/__init__.py` - Environment-based settings loader
- `config/settings/base.py` - Base Django settings (DRF, JWT, CORS, logging)
- `config/settings/development.py` - Development-specific settings
- `config/settings/production.py` - Production-specific settings
- `config/urls.py` - Main URL configuration with health endpoint
- `config/views.py` - Health check view
- `config/wsgi.py` - WSGI configuration

### Project Files
- `manage.py` - Django management script
- `requirements.txt` - Python dependencies
- `pytest.ini` - Pytest configuration
- `docker-compose.yml` - Postgres + Redis services
- `.env.example` - Environment variables template (see SETUP.md for content)

### Test Files
- `tests/__init__.py` - Tests package init
- `tests/conftest.py` - Pytest fixtures and configuration
- `tests/test_health.py` - Health endpoint test

### Documentation
- `SETUP.md` - Setup instructions
- `SCAFFOLD_FILES.md` - This file

## Key Features Implemented

### 1. Settings Structure (`config/settings/`)
- **base.py**: Core settings with DRF, SimpleJWT, CORS, logging
- **development.py**: Debug mode, verbose logging, CORS allows all
- **production.py**: Security headers, file logging, SSL settings
- **__init__.py**: Loads settings based on `ENVIRONMENT` variable

### 2. DRF Configuration
- JWT authentication as default
- JSON renderer/parser
- IsAuthenticated permission by default

### 3. SimpleJWT
- Access token: 1 hour lifetime
- Refresh token: 7 days lifetime
- Token rotation enabled
- Endpoints: `/api/token/`, `/api/token/refresh/`

### 4. CORS
- Configurable allowed origins via env
- Credentials support enabled
- Allows all in development

### 5. Logging
- Console handler with verbose formatter
- File handler in production
- Configurable log levels via env
- Django request errors logged

### 6. Docker Compose
- PostgreSQL 15 (alpine)
- Redis 7 (alpine)
- Health checks configured
- Persistent volumes

### 7. Pytest Setup
- pytest-django configured
- Coverage reporting
- Test discovery configured
- Database access enabled

### 8. Health Endpoint
- Route: `GET /health/`
- Returns: `{"status": "ok", "service": "django"}`
- Status: 200 OK
- Content-Type: application/json

## Verification Commands

```bash
# 1. Start services
docker-compose up -d

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Run server
python manage.py runserver

# 5. Test health endpoint
curl http://localhost:8000/health/

# 6. Run tests
pytest

# 7. Run tests with coverage
pytest --cov
```

## Environment Variables Required

See `.env.example` or `SETUP.md` for complete list. Key variables:
- `ENVIRONMENT` - development/production
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` - Database config
- `CORS_ALLOWED_ORIGINS` - CORS origins

