from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import SettingsUpdate
from app.services.settings_service import get_runtime_settings, update_runtime_settings

router = APIRouter()

@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    return get_runtime_settings(db)

@router.put("/settings")
def put_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    return update_runtime_settings(db, payload.model_dump(exclude_none=True))
