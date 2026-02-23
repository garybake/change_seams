"""Prompt registry CRUD API."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.prompt import PromptTemplate
from app.prompts.registry import activate_prompt, get_next_version

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


# ── Schemas ────────────────────────────────────────────────────────────────

class PromptCreate(BaseModel):
    key: str
    content: str
    purpose: str | None = None
    owner: str | None = None
    expected_inputs: dict[str, Any] | None = None
    expected_outputs: dict[str, Any] | None = None


class PromptOut(BaseModel):
    id: int
    key: str
    version: int
    content: str
    purpose: str | None
    owner: str | None
    expected_inputs: dict[str, Any] | None
    expected_outputs: dict[str, Any] | None
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}

    def model_post_init(self, __context: Any) -> None:
        # Serialize datetime to ISO string
        if hasattr(self, "__dict__"):
            pass

    @classmethod
    def from_orm_model(cls, p: PromptTemplate) -> "PromptOut":
        return cls(
            id=p.id,
            key=p.key,
            version=p.version,
            content=p.content,
            purpose=p.purpose,
            owner=p.owner,
            expected_inputs=p.expected_inputs,
            expected_outputs=p.expected_outputs,
            is_active=p.is_active,
            created_at=p.created_at.isoformat(),
        )


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("", response_model=list[PromptOut])
async def list_prompts(db: AsyncSession = Depends(get_db)) -> list[PromptOut]:
    """List the latest version of every prompt key."""
    from sqlalchemy import func

    # Subquery: max version per key
    subq = (
        select(PromptTemplate.key, func.max(PromptTemplate.version).label("max_version"))
        .group_by(PromptTemplate.key)
        .subquery()
    )
    result = await db.execute(
        select(PromptTemplate).join(
            subq,
            (PromptTemplate.key == subq.c.key)
            & (PromptTemplate.version == subq.c.max_version),
        )
    )
    prompts = result.scalars().all()
    return [PromptOut.from_orm_model(p) for p in prompts]


@router.get("/{key}", response_model=list[PromptOut])
async def get_prompt_versions(
    key: str, db: AsyncSession = Depends(get_db)
) -> list[PromptOut]:
    """Get all versions for a prompt key, newest first."""
    result = await db.execute(
        select(PromptTemplate)
        .where(PromptTemplate.key == key)
        .order_by(PromptTemplate.version.desc())
    )
    prompts = result.scalars().all()
    if not prompts:
        raise HTTPException(status_code=404, detail=f"No prompts found for key {key!r}")
    return [PromptOut.from_orm_model(p) for p in prompts]


@router.post("", response_model=PromptOut, status_code=201)
async def create_prompt(
    body: PromptCreate, db: AsyncSession = Depends(get_db)
) -> PromptOut:
    """Create a new prompt version. New versions are inactive by default."""
    version = await get_next_version(body.key, db)
    prompt = PromptTemplate(
        key=body.key,
        version=version,
        content=body.content,
        purpose=body.purpose,
        owner=body.owner,
        expected_inputs=body.expected_inputs,
        expected_outputs=body.expected_outputs,
        is_active=False,
    )
    db.add(prompt)
    await db.commit()
    await db.refresh(prompt)
    return PromptOut.from_orm_model(prompt)


@router.put("/{key}/{version}/activate", response_model=PromptOut)
async def activate_prompt_version(
    key: str, version: int, db: AsyncSession = Depends(get_db)
) -> PromptOut:
    """Set a specific version as active, deactivating all others for that key."""
    prompt = await activate_prompt(key, version, db)
    if prompt is None:
        raise HTTPException(
            status_code=404,
            detail=f"Prompt key={key!r} version={version} not found",
        )
    return PromptOut.from_orm_model(prompt)


@router.delete("/{prompt_id}", status_code=204)
async def delete_prompt(
    prompt_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a specific prompt row by ID."""
    result = await db.execute(
        select(PromptTemplate).where(PromptTemplate.id == prompt_id)
    )
    prompt = result.scalar_one_or_none()
    if prompt is None:
        raise HTTPException(status_code=404, detail=f"Prompt id={prompt_id} not found")
    await db.delete(prompt)
    await db.commit()
