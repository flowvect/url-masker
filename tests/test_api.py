"""Integration tests for FastAPI endpoints."""

import uuid
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_home_page(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    assert "URL Masker" in response.text

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

@pytest.mark.asyncio
async def test_create_and_redirect_link(client: AsyncClient):
    alias = f"alias_{uuid.uuid4().hex[:8]}"
    # 1. Create a link
    payload = {
        "long_url": "https://example.com/some/destination",
        "custom_alias": alias,
        "is_masked": False
    }
    response = await client.post("/api/links", json=payload)
    assert response.status_code == 201
    created_link = response.json()
    assert created_link["short_code"] == alias
    assert created_link["long_url"] == "https://example.com/some/destination"
    link_id = created_link["id"]

    # 2. Get link by ID
    get_res = await client.get(f"/api/links/{link_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == link_id

    # 3. List links
    list_res = await client.get("/api/links")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 4. Perform redirect
    redirect_res = await client.get(f"/{alias}", follow_redirects=False)
    assert redirect_res.status_code == 302
    assert redirect_res.headers["location"] == "https://example.com/some/destination"

    # 5. Check click count incremented
    get_res_after = await client.get(f"/api/links/{link_id}")
    assert get_res_after.json()["click_count"] == 1

    # 6. Update link
    patch_res = await client.patch(f"/api/links/{link_id}", json={"is_masked": True})
    assert patch_res.status_code == 200
    assert patch_res.json()["is_masked"] is True

    # 7. Delete link
    del_res = await client.delete(f"/api/links/{link_id}")
    assert del_res.status_code == 204

    # 8. Access deleted link redirect (should return 410)
    redirect_deleted = await client.get(f"/{alias}", follow_redirects=False)
    assert redirect_deleted.status_code == 410

@pytest.mark.asyncio
async def test_auto_generated_short_code(client: AsyncClient):
    payload = {
        "long_url": "https://python.org",
        "is_masked": False
    }
    response = await client.post("/api/links", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert len(data["short_code"]) > 0
    short_code = data["short_code"]

    # Redirect using generated short code
    redirect_res = await client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_res.status_code == 302
    assert redirect_res.headers["location"].rstrip("/") == "https://python.org"
