from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.analytics import dashboard_overview, landing_summary

router = APIRouter()


@router.get("/landing/summary")
def landing(db: Session = Depends(get_db)):
    return landing_summary(db)


@router.get("/dashboard/overview")
def overview(db: Session = Depends(get_db)):
    return dashboard_overview(db)
