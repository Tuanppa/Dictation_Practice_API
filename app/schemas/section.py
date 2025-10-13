from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID


# Base Schema
class SectionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    total_lessons: int = Field(default=0, ge=0)
    topic_id: UUID


# Schema cho việc tạo section mới
class SectionCreate(SectionBase):
    pass


# Schema cho việc cập nhật section
class SectionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    total_lessons: Optional[int] = Field(None, ge=0)
    topic_id: Optional[UUID] = None


# Schema trả về (response)
class SectionResponse(SectionBase):
    id: UUID
    
    model_config = ConfigDict(from_attributes=True)