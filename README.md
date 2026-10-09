# URL Shortener & Masking Tool

A high-performance URL shortening and masking (cloaking) service built with **FastAPI** and **PostgreSQL**.

## Features

- **URL Shortening** — Generate compact short codes via base62 encoding
- **URL Masking / Cloaking** — Serve destination content under your short domain *(Phase 2)*
- **Custom Aliases** — Choose your own short code
- **Link Expiration** — Set time-based or click-based limits
- **Click Analytics** — Track referrer, device, location *(Phase 4)*
- **User Accounts** — Register, login, manage your links *(Phase 3)*
- **Admin Dashboard** — Moderate links platform-wide *(Phase 5)*
- **REST API** — Full programmatic access with auto-generated docs

## Quick Start

### 1. Prerequisites
- Python 3.12+
- PostgreSQL 16+ (or use Docker Compose)
- Git

### 2. Clone & Setup

```bash
git clone <repo-url>
cd url-masker

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials
```

### 3. Start PostgreSQL (Docker)

```bash
docker compose up db -d
```

### 4. Run Migrations

```bash
alembic upgrade head
```

### 5. Start the Server

```bash
uvicorn app.main:app --reload
```

The API is now live at **http://localhost:8000**  
Interactive docs at **http://localhost:8000/docs**

## API Endpoints (Phase 1)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/links` | Create a short link |
| `GET`  | `/api/links` | List links |
| `GET`  | `/api/links/{id}` | Get link details |
| `GET`  | `/{short_code}` | Redirect to destination |

## Project Structure

```
url-masker/
  app/
    main.py              # FastAPI application entry point
    config.py            # Settings and environment variables
    models/              # SQLAlchemy ORM models
    schemas/             # Pydantic request/response schemas
    routers/             # API route handlers
    services/            # Business logic (shortener, masking, analytics)
    db/                  # Database session and migrations
    core/                # Security, caching, shared utilities
    templates/           # Server-rendered HTML pages
    static/              # CSS, JS, images
  tests/                 # Test suite
  docker-compose.yml     # PostgreSQL + app containers
  Dockerfile
  alembic.ini            # Database migration config
```

## License

MIT
