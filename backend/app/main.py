from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.approvals import router as approvals_router
from app.api.campaigns import router as campaigns_router
from app.api.content import router as content_router
from app.api.export import router as export_router
from app.api.planner import router as planner_router
from app.config import settings

app = FastAPI(
    title="AI Marketing Automation",
    description="Plan → Generate → Approve → Export to Google Drive & Sheets",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(campaigns_router, prefix="/api")
app.include_router(planner_router, prefix="/api")
app.include_router(content_router, prefix="/api")
app.include_router(approvals_router, prefix="/api")
app.include_router(export_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/")
async def root():
    return {
        "name": "AI Marketing Automation API",
        "docs": "/docs",
        "features": ["30-day calendar", "AIDA copywriting", "Canva designs", "Google Drive + Sheets export"],
    }
