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

    In development, auto-creates tables if DB is accessible.
    """
    if settings.ENVIRONMENT == "development":
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            print(f"Database initialization warning (check DATABASE_URL): {e}")
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
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"base_url": settings.BASE_URL},
    )


@app.get("/health", tags=["system"])
async def health_check():
    """Liveness probe for load balancers and container orchestrators."""
    return {"status": "ok", "version": app.version}


# ── Register routers ─────────────────────────────────────────────────────
app.include_router(links.router)
app.include_router(redirect.router)  # Must be last — catches /{short_code}
