from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID


# Base Schema
class AchievementBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Tên của thành tích")
    score: float = Field(default=0.0, ge=0, description="Điều kiện điểm số cần đạt")
    time: int = Field(default=0, ge=0, description="Điều kiện thời gian cần đạt (giây)")
    performance: float = Field(default=0.0, ge=0, description="Điều kiện hiệu suất cần đạt")


# Schema cho việc tạo achievement mới
class AchievementCreate(AchievementBase):
    pass


# Schema cho việc cập nhật achievement
class AchievementUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    score: Optional[float] = Field(None, ge=0)
    time: Optional[int] = Field(None, ge=0)
    performance: Optional[float] = Field(None, ge=0)


# Schema trả về (response)
class AchievementResponse(AchievementBase):
    id: UUID
    
    model_config = ConfigDict(from_attributes=True)