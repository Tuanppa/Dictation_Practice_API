from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base

# Import models TRƯỚC KHI tạo tables (quan trọng!)
from app.models import user, topic, lesson, section, progress  # noqa: F401

# Import routers (QUAN TRỌNG: import từ app.routers, không phải app.models)
from app.routers import auth, users, topics, lessons, sections, progress

# Tạo tables trong database
Base.metadata.create_all(bind=engine)

# Khởi tạo FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for Dictation Practice App - User Management System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Cấu hình CORS cho iOS app
origins = settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (đã sửa: thêm topics, lessons, sections, progresses)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX, tags=["Authentication"])
app.include_router(users.router, prefix=settings.API_V1_PREFIX, tags=["Users"])
app.include_router(topics.router, prefix=settings.API_V1_PREFIX, tags=["Topics"])
app.include_router(lessons.router, prefix=settings.API_V1_PREFIX, tags=["Lessons"])
app.include_router(sections.router, prefix=settings.API_V1_PREFIX, tags=["Sections"])
app.include_router(progress.router, prefix=settings.API_V1_PREFIX, tags=["Progress"])


@app.get("/")
async def root():
    """
    Root endpoint - Health check
    """
    return {
        "message": "Dictation Practice API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )