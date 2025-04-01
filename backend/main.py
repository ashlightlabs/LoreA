from fastapi import FastAPI
from app.api import lore

app = FastAPI()

app.include_router(lore.router, prefix="/lore")
