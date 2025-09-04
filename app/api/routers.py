from fastapi import APIRouter
from app.api.endpoints import check_fraud

router = APIRouter()

router.include_router(check_fraud.router, prefix="/check_fraud", tags=["check_fraud"])