import pdb
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from backend.app.services.core import add_lore_to_db, get_all_lore_from_db, get_filtered_lore

router = APIRouter()

class LoreEntry(BaseModel):
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)
    template: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Example Entry",
                "content": "Sample content",
                "tags": ["tag1", "tag2"],
                "template": "Character"
            }
        }
    }

@router.post("/add")
async def add_lore(entry: LoreEntry):
    try:
        add_lore_to_db(
            title=entry.title,
            content=entry.content,
            tags=entry.tags,
            template=entry.template
        )
        return {"status": "success", "message": "Lore added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all")
async def get_all_lore():
    try:
        return {"status": "success", "data": get_all_lore_from_db()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/entries")
async def get_entries(
    tag: Optional[List[str]] = Query(None),
    type: Optional[str] = Query(None, description="Template type (Character, Location, etc.)"),
    query: Optional[str] = Query(None, description="Search term for title and content")
):
    """Get filtered lore entries based on tags, type, and search query."""
    try:
        return {
            "status": "success",
            "data": get_filtered_lore(tags=tag, entry_type=type, query=query)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
