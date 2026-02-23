"""Tests for Seam 2: prompt registry CRUD and activation invariant."""
import pytest


async def seed_prompt(db, key="test.prompt", content="Hello {name}", version=1, is_active=True):
    from app.models.prompt import PromptTemplate

    p = PromptTemplate(
        key=key,
        version=version,
        content=content,
        purpose="Test prompt",
        owner="test",
        is_active=is_active,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


# ── Registry service tests ─────────────────────────────────────────────────

async def test_fetch_active_prompt_returns_content(db_session):
    from app.prompts.registry import fetch_active_prompt

    await seed_prompt(db_session, key="agent.system", content="Be helpful.", is_active=True)
    result = await fetch_active_prompt("agent.system", db_session)
    assert result is not None
    content, version = result
    assert content == "Be helpful."
    assert version == 1


async def test_fetch_active_prompt_returns_none_when_missing(db_session):
    from app.prompts.registry import fetch_active_prompt

    result = await fetch_active_prompt("nonexistent.key", db_session)
    assert result is None


async def test_activate_deactivates_others(db_session):
    from app.prompts.registry import activate_prompt
    from app.models.prompt import PromptTemplate
    from sqlalchemy import select

    # Create v1 (active) and v2 (inactive)
    p1 = await seed_prompt(db_session, key="my.prompt", version=1, is_active=True)
    p2 = await seed_prompt(db_session, key="my.prompt", version=2, is_active=False)

    # Activate v2 — should deactivate v1
    result = await activate_prompt("my.prompt", 2, db_session)
    assert result is not None
    assert result.is_active is True
    assert result.version == 2

    # Verify v1 is now inactive
    res = await db_session.execute(
        select(PromptTemplate).where(
            PromptTemplate.key == "my.prompt", PromptTemplate.version == 1
        )
    )
    p1_refreshed = res.scalar_one()
    assert p1_refreshed.is_active is False


async def test_activate_returns_none_for_missing_version(db_session):
    from app.prompts.registry import activate_prompt

    result = await activate_prompt("ghost.prompt", 99, db_session)
    assert result is None


# ── API endpoint tests ─────────────────────────────────────────────────────

async def test_list_prompts_empty(client):
    res = await client.get("/api/prompts")
    assert res.status_code == 200
    assert res.json() == []


async def test_create_prompt(client):
    res = await client.post(
        "/api/prompts",
        json={
            "key": "api.test",
            "content": "You are a test assistant.",
            "purpose": "Testing",
            "owner": "test-team",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["key"] == "api.test"
    assert data["version"] == 1
    assert data["is_active"] is False


async def test_create_prompt_increments_version(client):
    await client.post("/api/prompts", json={"key": "versioned.key", "content": "v1"})
    res = await client.post("/api/prompts", json={"key": "versioned.key", "content": "v2"})
    assert res.status_code == 201
    assert res.json()["version"] == 2


async def test_get_prompt_versions(client):
    await client.post("/api/prompts", json={"key": "multi.key", "content": "v1"})
    await client.post("/api/prompts", json={"key": "multi.key", "content": "v2"})

    res = await client.get("/api/prompts/multi.key")
    assert res.status_code == 200
    versions = res.json()
    assert len(versions) == 2
    # Newest first
    assert versions[0]["version"] == 2


async def test_get_prompt_versions_404(client):
    res = await client.get("/api/prompts/nonexistent.key")
    assert res.status_code == 404


async def test_activate_prompt_via_api(client):
    create_res = await client.post(
        "/api/prompts", json={"key": "activate.test", "content": "hello"}
    )
    version = create_res.json()["version"]

    res = await client.put(f"/api/prompts/activate.test/{version}/activate")
    assert res.status_code == 200
    assert res.json()["is_active"] is True


async def test_delete_prompt(client):
    create_res = await client.post(
        "/api/prompts", json={"key": "delete.test", "content": "bye"}
    )
    prompt_id = create_res.json()["id"]

    del_res = await client.delete(f"/api/prompts/{prompt_id}")
    assert del_res.status_code == 204

    list_res = await client.get("/api/prompts")
    ids = [p["id"] for p in list_res.json()]
    assert prompt_id not in ids
