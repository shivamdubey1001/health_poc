from fastapi import APIRouter
router = APIRouter()

@router.get("/health")
def health():
    return {"status":"ok", "service":"Humana Ahead API", "prototype_mode":True}
