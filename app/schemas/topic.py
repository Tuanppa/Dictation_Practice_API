from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID


# Base Schema
class TopicBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    level: str = Field(..., description="Level: A1, A2, B1, B2, C1, C2")
    lessons_count: int = Field(default=0, ge=0)
    image_name: Optional[str] = Field(None, max_length=255)
    has_video: bool = Field(default=False)


# Schema cho việc tạo topic mới
class TopicCreate(TopicBase):
    pass


# Schema cho việc cập nhật topic
class TopicUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    level: Optional[str] = None
    lessons_count: Optional[int] = Field(None, ge=0)
    image_name: Optional[str] = Field(None, max_length=255)
    has_video: Optional[bool] = None


# Schema trả về (response)
class TopicResponse(TopicBase):
    id: UUID
    
    model_config = ConfigDict(from_attributes=True)