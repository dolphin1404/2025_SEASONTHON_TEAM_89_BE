import datetime
from fastapi import APIRouter

from app.schemas.check_fraud import ChatRequest

router = APIRouter()


@router.post("/")
async def check_fraud(data: ChatRequest):
    ...