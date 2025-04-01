from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter()

class LoreEntry(BaseModel):
    id: int
    title: str
    content: str
    tags: List[str]

fake_db = []

@router.post("/add")
def add_lore(entry: LoreEntry):
    fake_db.append(entry)
    return {"message": "Lore added successfully"}

@router.get("/all")
def get_all_lore():
    return fake_db
