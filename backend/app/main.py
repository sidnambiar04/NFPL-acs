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

# Configure CORS for local development and hosted frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
