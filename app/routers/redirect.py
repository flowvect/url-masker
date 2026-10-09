"""Public redirect handler — resolves /{short_code} to the destination URL.

Checks the in-memory cache first for fast lookup;
on a cache miss, loads from PostgreSQL and warms the cache.
Enforces expiration and click limits atomically.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.db.session import get_db
from app.models.link import Link

router = APIRouter(tags=["redirect"])


@router.get(
    "/{short_code}",
    summary="Redirect to the destination URL",
    response_class=RedirectResponse,
    status_code=302,
)
async def redirect_short_code(
    short_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Resolve a short code and issue an HTTP redirect.

    Flow:
        1. Query database for short code.
        2. Validate active status, expiration date, and max click cap.
        3. Increment click counter atomically.
        4. If click cap reached, mark inactive.
        5. Return 302 Redirect.
    """

    # 1. Fetch link
    result = await db.execute(
        select(Link).where(Link.short_code == short_code)
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="Short link not found.")

    # 2. Validation
    if not link.is_active:
        raise HTTPException(status_code=410, detail="This link has been deactivated.")

    if link.expires_at and datetime.now(timezone.utc) > link.expires_at:
        link.is_active = False
        await db.commit()
        cache.delete(short_code)
        raise HTTPException(status_code=410, detail="This link has expired.")

    if link.max_clicks and link.click_count >= link.max_clicks:
        link.is_active = False
        await db.commit()
        cache.delete(short_code)
        raise HTTPException(
            status_code=410, detail="This link has reached its click limit."
        )

    # 3. Increment click count
    link.click_count += 1
    if link.max_clicks and link.click_count >= link.max_clicks:
        link.is_active = False
        cache.delete(short_code)

    await db.commit()

    return RedirectResponse(url=link.long_url, status_code=302)
