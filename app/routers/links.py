"""Link management endpoints — create, list, get, update, delete."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import cache
from app.db.session import get_db
from app.models.link import Link, link_id_seq
from app.schemas.link import (
    LinkCreate,
    LinkListResponse,
    LinkResponse,
    LinkUpdate,
)
from app.services.shortener import encode

router = APIRouter(prefix="/api/links", tags=["links"])


# ── Helpers ───────────────────────────────────────────────────────────────

def _link_to_response(link: Link) -> LinkResponse:
    """Map an ORM Link to a public response, injecting the full short URL."""
    return LinkResponse(
        id=link.id,
        short_code=link.short_code,
        short_url=f"{settings.BASE_URL}/{link.short_code}",
        long_url=link.long_url,
        is_masked=link.is_masked,
        custom_alias=link.custom_alias,
        expires_at=link.expires_at,
        max_clicks=link.max_clicks,
        click_count=link.click_count,
        is_active=link.is_active,
        created_at=link.created_at,
    )


def _validate_url_scheme(url: str) -> None:
    """Block unsafe URI schemes (javascript:, data:, etc.)."""
    allowed = {"http", "https"}
    scheme = url.split("://")[0].lower() if "://" in url else ""
    if scheme not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"URL scheme '{scheme}' is not allowed. Use http or https.",
        )


# ── POST /api/links — Create a new short link ────────────────────────────

@router.post(
    "",
    response_model=LinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a short or masked link",
)
async def create_link(
    body: LinkCreate,
    db: AsyncSession = Depends(get_db),
) -> LinkResponse:
    long_url = str(body.long_url)
    _validate_url_scheme(long_url)

    # Custom alias — check uniqueness
    if body.custom_alias:
        exists = await db.execute(
            select(Link).where(Link.short_code == body.custom_alias)
        )
        if exists.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Alias '{body.custom_alias}' is already taken.",
            )
        short_code = body.custom_alias
        # We still need a sequence_id for record keeping
        seq_val = await db.execute(link_id_seq.next_value())
        sequence_id = seq_val.scalar()
    else:
        # Generate short code from sequence
        seq_val = await db.execute(link_id_seq.next_value())
        sequence_id = seq_val.scalar()
        short_code = encode(sequence_id)

    link = Link(
        short_code=short_code,
        long_url=long_url,
        is_masked=body.is_masked,
        custom_alias=body.custom_alias,
        expires_at=body.expires_at,
        max_clicks=body.max_clicks,
        sequence_id=sequence_id,
    )

    db.add(link)
    await db.commit()
    # Warm the cache
    cache.set(short_code, link.long_url)

    return _link_to_response(link)


# ── GET /api/links — List links (paginated) ──────────────────────────────

@router.get(
    "",
    response_model=LinkListResponse,
    summary="List links",
)
async def list_links(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> LinkListResponse:
    total_result = await db.execute(select(func.count(Link.id)))
    total = total_result.scalar() or 0

    result = await db.execute(
        select(Link).order_by(Link.created_at.desc()).offset(skip).limit(limit)
    )
    links = result.scalars().all()

    return LinkListResponse(
        items=[_link_to_response(link) for link in links],
        total=total,
    )


# ── GET /api/links/{link_id} — Get link details ─────────────────────────

@router.get(
    "/{link_id}",
    response_model=LinkResponse,
    summary="Get link details",
)
async def get_link(
    link_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> LinkResponse:
    result = await db.execute(select(Link).where(Link.id == link_id))
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found.")
    return _link_to_response(link)


# ── PATCH /api/links/{link_id} — Update a link ──────────────────────────

@router.patch(
    "/{link_id}",
    response_model=LinkResponse,
    summary="Update a link",
)
async def update_link(
    link_id: uuid.UUID,
    body: LinkUpdate,
    db: AsyncSession = Depends(get_db),
) -> LinkResponse:
    result = await db.execute(select(Link).where(Link.id == link_id))
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found.")

    update_data = body.model_dump(exclude_unset=True)

    # If changing the alias, ensure it's unique
    if "custom_alias" in update_data and update_data["custom_alias"]:
        alias = update_data["custom_alias"]
        exists = await db.execute(
            select(Link).where(Link.short_code == alias, Link.id != link_id)
        )
        if exists.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Alias '{alias}' is already taken.",
            )
        # Invalidate old cache entry and update short_code
        cache.delete(link.short_code)
        link.short_code = alias

    for field, value in update_data.items():
        if field != "custom_alias" or value is None:
            setattr(link, field, value)

    await db.commit()
    await db.refresh(link)

    # Refresh cache
    cache.set(link.short_code, link.long_url)

    return _link_to_response(link)


# ── DELETE /api/links/{link_id} — Deactivate a link ─────────────────────

@router.delete(
    "/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Deactivate (soft-delete) a link",
)
async def delete_link(
    link_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    result = await db.execute(select(Link).where(Link.id == link_id))
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found.")

    link.is_active = False
    await db.commit()

    # Remove from cache
    cache.delete(link.short_code)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
