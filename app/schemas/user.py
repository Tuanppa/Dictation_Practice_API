from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime, date
from app.models.user import GenderEnum, RoleEnum, AuthProviderEnum


# Base Schema
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[GenderEnum] = None


# Schema cho việc tạo user mới
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    

# Schema cho việc đăng ký bằng OAuth
class UserOAuthCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    auth_provider: AuthProviderEnum
    provider_id: str


# Schema cho việc cập nhật user
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[GenderEnum] = None
    

# Schema cho việc cập nhật password
class UserPasswordUpdate(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


# Schema cho việc cập nhật premium
class UserPremiumUpdate(BaseModel):
    is_premium: bool
    premium_start_date: Optional[datetime] = None
    premium_end_date: Optional[datetime] = None


# Schema cho việc cập nhật achievements
class UserAchievementsUpdate(BaseModel):
    achievements: Dict[str, Any] = Field(..., description="Các thành tích đạt được")


# Schema trả về thông tin user (không có password)
class UserResponse(UserBase):
    id: int
    auth_provider: AuthProviderEnum
    role: RoleEnum
    is_premium: bool
    premium_start_date: Optional[datetime] = None
    premium_end_date: Optional[datetime] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    score: float = Field(default=0.0, description="Điểm số tích lũy")
    time: int = Field(default=0, description="Tổng thời gian đã học (giây)")
    achievements: Optional[Dict[str, Any]] = Field(None, description="Các thành tích đạt được")
    
    model_config = ConfigDict(from_attributes=True)


# Schema cho login
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Schema cho token response
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


# Schema cho refresh token
class RefreshToken(BaseModel):
    refresh_token: str


# Schema cho user statistics (thống kê)
class UserStats(BaseModel):
    user_id: int
    total_score: float
    total_time: int
    total_lessons_completed: int
    total_lessons_in_progress: int
    average_rating: float
    achievements_count: int
    achievements: Optional[Dict[str, Any]] = None