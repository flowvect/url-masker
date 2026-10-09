"""FastAPI application entry point.

Creates the app, registers routers, and sets up lifecycle events.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.db.session import engine
from app.models import Base
from app.routers import links, redirect

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle.

    Auto-creates database tables when DB is connected.
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"Database initialization notice (check DATABASE_URL): {e}")
    yield
    try:
        await engine.dispose()
    except Exception:
        pass


app = FastAPI(
    title="URL Shortener & Masking Tool",
    description=(
        "Shorten URLs, cloak destinations, and track clicks — "
        "all with a fast REST API."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS (permissive in dev, tighten for production) ──────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home_page(request: Request):
    """Serve the Web UI for shortening and masking URLs."""
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    forwarded_host = request.headers.get("x-forwarded-host", request.headers.get("host"))
    current_url = f"{forwarded_proto}://{forwarded_host}".rstrip("/") if forwarded_host else settings.effective_base_url
    
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "base_url": current_url,
            "github_url": settings.GITHUB_REPO_URL,
            "environment": settings.ENVIRONMENT,
            "is_serverless": settings.is_serverless,
        },
    )


@app.get("/health", tags=["system"])
async def health_check():
    """Liveness probe for load balancers and container orchestrators."""
    return {"status": "ok", "version": app.version}


# ── Register routers ─────────────────────────────────────────────────────
app.include_router(links.router)
app.include_router(redirect.router)  # Must be last — catches /{short_code}
