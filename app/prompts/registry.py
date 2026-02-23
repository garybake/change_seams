"""
Seam 2 — Prompt Registry.

fetch_active_prompt() is called before every agent invocation.
The active prompt for a key can be swapped at runtime via the CRUD API
without restarting the server.
"""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt import PromptTemplate


async def fetch_active_prompt(key: str, db: AsyncSession) -> tuple[str, int] | None:
    """Return (content, version) for the active prompt with the given key, or None."""
    result = await db.execute(
        select(PromptTemplate)
        .where(PromptTemplate.key == key, PromptTemplate.is_active == True)  # noqa: E712
        .limit(1)
    )
    prompt = result.scalar_one_or_none()
    if prompt is None:
        return None
    return prompt.content, prompt.version


async def get_next_version(key: str, db: AsyncSession) -> int:
    """Return the next version number for a key (max existing + 1, or 1)."""
    from sqlalchemy import func

    result = await db.execute(
        select(func.max(PromptTemplate.version)).where(PromptTemplate.key == key)
    )
    max_version = result.scalar_one_or_none()
    return (max_version or 0) + 1


async def activate_prompt(key: str, version: int, db: AsyncSession) -> PromptTemplate | None:
    """Deactivate all versions of key, then activate the given version."""
    # Deactivate all
    await db.execute(
        update(PromptTemplate)
        .where(PromptTemplate.key == key)
        .values(is_active=False)
    )
    # Activate target
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.key == key, PromptTemplate.version == version
        )
    )
    prompt = result.scalar_one_or_none()
    if prompt is None:
        await db.rollback()
        return None
    prompt.is_active = True
    await db.commit()
    await db.refresh(prompt)
    return prompt
