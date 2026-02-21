from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time
from contextlib import asynccontextmanager

from .routes import validation, auth, analytics, health, billing
from ..db.connection import init_db, close_db
from ..config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await init_db()
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")
        print("API will start but database features may not work.")
    yield
    # Shutdown
    try:
        await close_db()
    except:
        pass


app = FastAPI(
    title="TruthChain API",
    description="AI Validation as a Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware — origins from CORS_ORIGINS env var ("*" only in development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if settings.is_production else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Include routers
app.include_router(validation.router)
app.include_router(auth.router)
app.include_router(analytics.router)
app.include_router(health.router)
app.include_router(billing.router)

@app.get("/")
async def root():
    return {
        "service": "TruthChain API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "docs": "/docs",
            "auth": "/v1/auth/signup",
            "validation": "/v1/validate",
            "analytics": "/v1/analytics/overview",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
