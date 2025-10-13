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
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="API Documentation",
        routes=app.routes,
    )
    
    # Thêm security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
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

@app.on_event("startup")
async def create_first_admin():
    """Tạo admin user đầu tiên nếu chưa có"""
    from app.core.database import SessionLocal
    from app.models.user import User, RoleEnum
    from app.core.security import get_password_hash
    
    db = SessionLocal()
    try:
        # Kiểm tra xem đã có admin chưa
        admin_exists = db.query(User).filter(User.role == RoleEnum.ADMIN).first()
        
        if not admin_exists:
            # Tạo admin đầu tiên
            admin_user = User(
                email="admin@example.com",
                username="admin",
                hashed_password=get_password_hash("admin123"),  # Đổi password này!
                full_name="System Admin",
                role=RoleEnum.ADMIN,
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            print("✅ First admin user created: admin@example.com / admin123")
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

