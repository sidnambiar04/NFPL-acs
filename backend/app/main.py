import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
import app.models  # Ensure all models are registered with Base.metadata
from app.api import auth, jobs, access, work_queue, admin, audit, parser
from app.seed import seed_initial_demo_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all database tables automatically on startup
    Base.metadata.create_all(bind=engine)
    # Check and seed sample demo data if empty
    seed_initial_demo_data()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Explainable, Policy-driven Access Control Service for Nagarkot Forwarders Pvt. Ltd.",
    lifespan=lifespan
)

# Configure CORS — allow any Vercel/Render subdomain + localhost for dev
_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
_extra = [o.strip() for o in _raw_origins.split(",") if o.strip()]
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    *_extra,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.(vercel\.app|onrender\.com)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers under /api
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(jobs.router, prefix=settings.API_V1_STR)
app.include_router(access.router, prefix=settings.API_V1_STR)
app.include_router(work_queue.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)
app.include_router(parser.router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "service": settings.PROJECT_NAME,
        "status": "online",
        "docs": "/docs",
        "policy_version": settings.POLICY_VERSION
    }

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "policy_version": settings.POLICY_VERSION}
