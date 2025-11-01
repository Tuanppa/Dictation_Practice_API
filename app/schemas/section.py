from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID


# Base Schema
class SectionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    total_lessons: int = Field(default=0, ge=0)
    topic_id: UUID
    order_index: int = Field(default=0, ge=0, description="Thứ tự hiển thị")
    is_visible: bool = Field(default=True, description="Cho phép hiển thị")


# Schema cho việc tạo section mới
class SectionCreate(SectionBase):
    pass


# Schema cho việc cập nhật section
class SectionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    total_lessons: Optional[int] = Field(None, ge=0)
    topic_id: Optional[UUID] = None
    order_index: Optional[int] = Field(None, ge=0)
    is_visible: Optional[bool] = None


# Schema trả về (response)
class SectionResponse(SectionBase):
    id: UUID
    
    model_config = ConfigDict(from_attributes=True)