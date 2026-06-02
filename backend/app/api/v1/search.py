from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.db.session import get_db
from app.models.models import Project, Task, User
from app.schemas.schemas import SemanticSearchRequest, SemanticSearchResult, ProjectOut, TaskOut
from app.core.deps import get_current_user
from app.services.embedding import semantic_search
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/keyword")
async def keyword_search(
    q: str = Query(min_length=2),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full-text keyword search across projects and tasks."""
    like = f"%{q}%"

    projects_res = await db.execute(
        select(Project)
        .options(selectinload(Project.owner), selectinload(Project.tasks),
                 selectinload(Project.insights), selectinload(Project.health_records))
        .where(or_(Project.title.ilike(like), Project.description.ilike(like)))
        .limit(20)
    )
    projects = [ProjectOut.model_validate(p) for p in projects_res.scalars().all()]

    tasks_res = await db.execute(
        select(Task)
        .options(selectinload(Task.assignee))
        .where(or_(Task.title.ilike(like), Task.description.ilike(like)))
        .limit(20)
    )
    tasks = [TaskOut.model_validate(t) for t in tasks_res.scalars().all()]

    return {"projects": projects, "tasks": tasks, "query": q}


@router.post("/semantic", response_model=List[SemanticSearchResult])
async def semantic_search_endpoint(
    payload: SemanticSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Semantic similarity search using pgvector.
    Example: "What projects are blocked because of APIs?"
    """
    results = await semantic_search(
        db=db,
        query=payload.query,
        content_types=payload.content_types,
        limit=payload.limit,
    )
    return [SemanticSearchResult(**r) for r in results]
