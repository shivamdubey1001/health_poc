from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.analytics import cost_analytics

router = APIRouter()

@router.get("/analytics/cost")
def cost(db: Session = Depends(get_db)):
    return cost_analytics(db)
