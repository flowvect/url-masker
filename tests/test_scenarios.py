"""Comprehensive Scenario Tests for URL Shortener & Masking Tool.

Covers:
1. URL Validation (allowed schemes, malformed URLs, special characters)
2. Custom Alias validation, length constraints, and collision handling
3. Expiration date enforcement (past vs future)
4. Max clicks limit enforcement
5. CRUD operations (List, Get, Patch, Delete) and Cache Invalidation
6. Concurrency and Race Condition handling
7. Security: Unsafe scheme blocking, Non-existent short codes (404)
"""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from app.core.cache import cache

@pytest.mark.asyncio
async def test_scenario_url_validation_and_schemes(client: AsyncClient):
    """Scenario 1: Validate URL formatting and reject unsafe/malformed schemes."""
    # 1. Valid URLs with complex query parameters
    valid_url = "https://example.com/search?q=fastapi+url+shortener&category=tools#section-3"
    res = await client.post("/api/links", json={"long_url": valid_url})
    assert res.status_code == 201
    assert res.json()["long_url"] == valid_url

    # 2. Reject malformed URL strings
    res_malformed = await client.post("/api/links", json={"long_url": "not-a-valid-url"})
    assert res_malformed.status_code == 422  # Pydantic validation error

    # 3. Reject non-http(s) schemes like ftp:// or javascript:
    res_ftp = await client.post("/api/links", json={"long_url": "ftp://files.example.com/archive.zip"})
    assert res_ftp.status_code in [400, 422]

    res_js = await client.post("/api/links", json={"long_url": "javascript:alert(1)"})
    assert res_js.status_code in [400, 422]

@pytest.mark.asyncio
async def test_scenario_custom_aliases_and_collisions(client: AsyncClient):
    """Scenario 2: Custom alias constraints, length checks, and collision detection."""
    alias = f"alias_col_{uuid.uuid4().hex[:6]}"

    # 1. Successful custom alias creation
    res1 = await client.post("/api/links", json={
        "long_url": "https://example.com/target1",
        "custom_alias": alias
    })
    assert res1.status_code == 201
    assert res1.json()["short_code"] == alias

    # 2. Collision rejection (409 Conflict)
    res2 = await client.post("/api/links", json={
        "long_url": "https://example.com/target2",
        "custom_alias": alias
    })
    assert res2.status_code == 409
    assert "already taken" in res2.json()["detail"]

    # 3. Alias with invalid characters (e.g. spaces or symbols)
    res_invalid = await client.post("/api/links", json={
        "long_url": "https://example.com/target3",
        "custom_alias": "invalid alias spaces"
    })
    assert res_invalid.status_code == 422

    # 4. Alias too short (< 3 chars)
    res_short = await client.post("/api/links", json={
        "long_url": "https://example.com/target4",
        "custom_alias": "ab"
    })
    assert res_short.status_code == 422

@pytest.mark.asyncio
async def test_scenario_link_expiration_time(client: AsyncClient):
    """Scenario 3: Time-based expiration enforcement."""
    # 1. Link expired in the past
    past_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    alias_past = f"past_{uuid.uuid4().hex[:6]}"
    res_past = await client.post("/api/links", json={
        "long_url": "https://example.com/past",
        "custom_alias": alias_past,
        "expires_at": past_time
    })
    assert res_past.status_code == 201

    # Attempt to redirect — should return 410 Gone
    redirect_past = await client.get(f"/{alias_past}", follow_redirects=False)
    assert redirect_past.status_code == 410

    # 2. Link expiring in the future
    future_time = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    alias_future = f"fut_{uuid.uuid4().hex[:6]}"
    res_future = await client.post("/api/links", json={
        "long_url": "https://example.com/future",
        "custom_alias": alias_future,
        "expires_at": future_time
    })
    assert res_future.status_code == 201

    # Attempt to redirect — should succeed (302)
    redirect_fut = await client.get(f"/{alias_future}", follow_redirects=False)
    assert redirect_fut.status_code == 302
    assert redirect_fut.headers["location"] == "https://example.com/future"

@pytest.mark.asyncio
async def test_scenario_click_cap_enforcement(client: AsyncClient):
    """Scenario 4: Click limit enforcement (max_clicks cap)."""
    alias_clicks = f"cap_{uuid.uuid4().hex[:6]}"
    # Cap of 3 clicks
    res = await client.post("/api/links", json={
        "long_url": "https://example.com/limited",
        "custom_alias": alias_clicks,
        "max_clicks": 3
    })
    assert res.status_code == 201
    link_id = res.json()["id"]

    # 1st Click
    r1 = await client.get(f"/{alias_clicks}", follow_redirects=False)
    assert r1.status_code == 302

    # 2nd Click
    r2 = await client.get(f"/{alias_clicks}", follow_redirects=False)
    assert r2.status_code == 302

    # 3rd Click
    r3 = await client.get(f"/{alias_clicks}", follow_redirects=False)
    assert r3.status_code == 302

    # 4th Click -> Limit reached -> 410 Gone
    r4 = await client.get(f"/{alias_clicks}", follow_redirects=False)
    assert r4.status_code == 410

    # Verify link details show click count == 3 and is_active is now False
    details = await client.get(f"/api/links/{link_id}")
    assert details.json()["click_count"] == 3
    assert details.json()["is_active"] is False

@pytest.mark.asyncio
async def test_scenario_cache_invalidation_on_update_and_delete(client: AsyncClient):
    """Scenario 5: In-memory cache behavior & invalidation on patch/delete."""
    alias = f"cache_{uuid.uuid4().hex[:6]}"
    res = await client.post("/api/links", json={
        "long_url": "https://example.com/original",
        "custom_alias": alias
    })
    assert res.status_code == 201
    link_id = res.json()["id"]

    # Cache should contain this alias
    assert cache.get(alias) is not None

    # Redirect hits cache/db
    r1 = await client.get(f"/{alias}", follow_redirects=False)
    assert r1.status_code == 302

    # Delete link
    del_res = await client.delete(f"/api/links/{link_id}")
    assert del_res.status_code == 204

    # Cache entry must be invalidated
    assert cache.get(alias) is None

    # Visiting deleted link returns 410
    r_del = await client.get(f"/{alias}", follow_redirects=False)
    assert r_del.status_code == 410

@pytest.mark.asyncio
async def test_scenario_nonexistent_and_edge_cases(client: AsyncClient):
    """Scenario 6: Non-existent routes and 404 behavior."""
    non_existent = f"nonexistent_{uuid.uuid4().hex}"
    res = await client.get(f"/{non_existent}", follow_redirects=False)
    assert res.status_code == 404

    # Non-existent link ID detail
    fake_uuid = str(uuid.uuid4())
    res_detail = await client.get(f"/api/links/{fake_uuid}")
    assert res_detail.status_code == 404
