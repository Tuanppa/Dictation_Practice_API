from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Database - Railway sẽ tự động set DATABASE_URL
    # Pydantic-settings tự động đọc từ environment variables
    DATABASE_URL: str = "postgresql://localhost/dictation_practice_db"
    
    # Redis - Railway sẽ tự động set REDIS_URL
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None  # Railway format: redis://...
    
    # JWT
    SECRET_KEY: str = "development-secret-key-please-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # OAuth - Google
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    
    # OAuth - Apple
    APPLE_CLIENT_ID: Optional[str] = None
    APPLE_TEAM_ID: Optional[str] = None
    APPLE_KEY_ID: Optional[str] = None
    APPLE_PRIVATE_KEY_PATH: Optional[str] = None
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Dictation Practice API"
    
    # CORS - Cho phép iOS app connect
    ALLOWED_ORIGINS: str = "*"  # Trong production nên set cụ thể
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # Pydantic sẽ tự động đọc environment variables
        # và override các giá trị default


settings = Settings()

# Debug log (chỉ hiển thị một phần để bảo mật)
if os.getenv("ENVIRONMENT") != "production":
    db_url_preview = settings.DATABASE_URL[:40] + "..." if len(settings.DATABASE_URL) > 40 else settings.DATABASE_URL
    print(f"🔍 Config loaded - DATABASE_URL: {db_url_preview}")