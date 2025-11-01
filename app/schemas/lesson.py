from pydantic import BaseModel, Field, ConfigDict, HttpUrl
from typing import Optional
from uuid import UUID


# Base Schema
class LessonBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    subtitle: Optional[str] = Field(None, max_length=500)
    parts: int = Field(default=0, ge=0, description="Số phần trong bài học")
    level: str = Field(..., description="Level: A1, A2, B1, B2, C1, C2")
    is_premium: bool = Field(default=False)
    url_media: Optional[str] = Field(None, max_length=500)
    url_script: Optional[str] = Field(None, max_length=500)
    section_id: UUID
    order_index: int = Field(default=0, ge=0, description="Thứ tự hiển thị")
    is_visible: bool = Field(default=True, description="Cho phép hiển thị")


# Schema cho việc tạo lesson mới
class LessonCreate(LessonBase):
    pass


# Schema cho việc cập nhật lesson
class LessonUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    subtitle: Optional[str] = Field(None, max_length=500)
    parts: Optional[int] = Field(None, ge=0)
    level: Optional[str] = None
    is_premium: Optional[bool] = None
    url_media: Optional[str] = Field(None, max_length=500)
    url_script: Optional[str] = Field(None, max_length=500)
    section_id: Optional[UUID] = None
    order_index: Optional[int] = Field(None, ge=0)
    is_visible: Optional[bool] = None


# Schema trả về (response)
class LessonResponse(LessonBase):
    id: UUID
    
    model_config = ConfigDict(from_attributes=True)


# Schema với progress info (cho user)
class LessonWithProgress(LessonResponse):
    completed_parts: int = Field(default=0)
    star_rating: int = Field(default=0)
    is_completed: bool = Field(default=False)
    score: float = Field(default=0.0)
    time: int = Field(default=0)