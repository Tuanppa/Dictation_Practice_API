from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


# Base Schema
class ProgressBase(BaseModel):
    completed_parts: int = Field(default=0, ge=0)
    star_rating: int = Field(default=0, ge=0, le=5, description="Rating từ 0-5 sao")
    lesson_id: UUID


# Schema cho việc tạo/cập nhật progress
class ProgressCreate(ProgressBase):
    pass


class ProgressUpdate(BaseModel):
    completed_parts: Optional[int] = Field(None, ge=0)
    star_rating: Optional[int] = Field(None, ge=0, le=5)


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