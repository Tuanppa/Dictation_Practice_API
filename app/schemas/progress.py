from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


# Base Schema
class ProgressBase(BaseModel):
    completed_parts: int = Field(default=0, ge=0)
    star_rating: int = Field(default=0, ge=0, le=5, description="Rating từ 0-5 sao")
    lesson_id: UUID
    score: float = Field(default=0.0, ge=0, description="Điểm số đạt được")
    time: int = Field(default=0, ge=0, description="Thời gian thực hành (giây)")
    skip: int = Field(default=0, ge=0, description="Số lần ấn skip")
    play_again: int = Field(default=0, ge=0, description="Số lần ấn nút nghe lại")
    check: int = Field(default=0, ge=0, description="Số lần ấn gợi ý")


# Schema cho việc tạo/cập nhật progress
class ProgressCreate(ProgressBase):
    pass


class ProgressUpdate(BaseModel):
    completed_parts: Optional[int] = Field(None, ge=0)
    star_rating: Optional[int] = Field(None, ge=0, le=5)
    score: Optional[float] = Field(None, ge=0)
    time: Optional[int] = Field(None, ge=0)
    skip: Optional[int] = Field(None, ge=0)
    play_again: Optional[int] = Field(None, ge=0)
    check: Optional[int] = Field(None, ge=0)


# Schema trả về (response)
class ProgressResponse(ProgressBase):
    id: UUID
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Schema thống kê progress
class ProgressStats(BaseModel):
    total_lessons: int
    completed_lessons: int
    in_progress_lessons: int
    average_rating: float
    total_parts_completed: int
    total_score: float = Field(default=0.0, description="Tổng điểm số")
    total_time: int = Field(default=0, description="Tổng thời gian học (giây)")
    average_score: float = Field(default=0.0, description="Điểm trung bình")