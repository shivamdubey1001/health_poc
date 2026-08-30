from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.services.ingestion import initialize_database
from app.api.routes import health, members, agents, dashboard, queue, outreach, analytics, settings as settings_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in [health.router, members.router, agents.router, dashboard.router, queue.router, outreach.router, analytics.router, settings_routes.router]:
    app.include_router(router, prefix=settings.api_prefix)

@app.get("/")
def root():
    return {"message":"Humana Ahead API", "docs":"/docs", "prototype_mode":True}
