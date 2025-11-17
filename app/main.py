"""
FastAPI Main Application with Avatar Support
File: app/main.py
Railway + Cloudinary Ready
Version: 1.2.0
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base

# Import models
from app.models import user, topic, lesson, section, achievement, top_performance, progress  # noqa: F401

# Import routers
from app.routers import (
    auth, 
    users, 
    topics, 
    lessons, 
    sections,
    progress as progress_router,
    achievements,
    rankings
)

# Tạo tables trong database
Base.metadata.create_all(bind=engine)

# Khởi tạo FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for Dictation Practice App - User Management with Avatar Support (Cloudinary)",
    version="1.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={
        "persistAuthorization": True,
    }
)

# Cấu hình CORS
origins = settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX, tags=["Authentication"])
app.include_router(users.router, prefix=settings.API_V1_PREFIX, tags=["Users"])
app.include_router(topics.router, prefix=settings.API_V1_PREFIX, tags=["Topics"])
app.include_router(lessons.router, prefix=settings.API_V1_PREFIX, tags=["Lessons"])
app.include_router(sections.router, prefix=settings.API_V1_PREFIX, tags=["Sections"])
app.include_router(progress_router.router, prefix=settings.API_V1_PREFIX, tags=["Progress"])
app.include_router(achievements.router, prefix=settings.API_V1_PREFIX, tags=["Achievements"])
app.include_router(rankings.router, prefix=settings.API_V1_PREFIX, tags=["Rankings & Leaderboard"])


@app.get("/")
async def root():
    """Root endpoint - Health check"""
    return {
        "message": "Dictation Practice API is running",
        "version": "1.2.0",
        "docs": "/docs",
        "features": [
            "User Authentication",
            "Learning Progress Tracking",
            "Achievements System",
            "Leaderboard & Rankings",
            "Avatar Upload (Cloudinary)"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with Cloudinary status"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
    }


@app.on_event("startup")
async def startup_event():
    """Startup events - Create admin & check Cloudinary"""
    
    # 1. Create first admin user
    await create_first_admin()


async def create_first_admin():
    """Tạo admin user đầu tiên nếu chưa có"""
    from app.core.database import SessionLocal
    from app.models.user import User, RoleEnum, AuthProviderEnum
    from app.core.security import get_password_hash
    
    db = SessionLocal()
    try:
        admin_exists = db.query(User).filter(User.role == RoleEnum.ADMIN).first()
        
        if not admin_exists:
            admin_user = User(
                email="admin@vnbrain.vn",
                hashed_password=get_password_hash("admin123"),
                full_name="System Admin",
                role=RoleEnum.ADMIN,
                auth_provider=AuthProviderEnum.EMAIL,
                is_active=True,
                is_verified=True,
                score=0.0,
                time=0,
                achievements={},
                avatar_url=None
            )
            db.add(admin_user)
            db.commit()
            print("✅ First admin user created!")
            print("   📧 Email: admin@vnbrain.vn")
            print("   🔑 Password: admin123")
            print("   ⚠️  Please change password after first login!")
        else:
            print("✅ Admin user already exists")
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )