from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from enum import Enum


# Enum cho ranking mode
class RankingMode(str, Enum):
    ALL_TIME = "all_time"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    BY_LESSON = "by_lesson"


# Base Schema
class TopPerformanceBase(BaseModel):
    mode: RankingMode = Field(..., description="Chế độ xếp hạng")
    user_id: int = Field(..., description="ID người dùng")
    rank: int = Field(..., ge=1, description="Thứ tự xếp hạng")
    score: float = Field(default=0.0, ge=0, description="Điểm số đạt được")
    time: int = Field(default=0, ge=0, description="Thời gian thực hành (giây)")
    performance: float = Field(default=0.0, ge=0, description="Hiệu suất tổng thể")
    lesson_id: Optional[UUID] = Field(None, description="ID bài học (chỉ dùng cho chế độ by_lesson)")


# Schema cho việc tạo ranking mới
class TopPerformanceCreate(TopPerformanceBase):
    pass


# Schema cho việc cập nhật ranking
class TopPerformanceUpdate(BaseModel):
    rank: Optional[int] = Field(None, ge=1)
    score: Optional[float] = Field(None, ge=0)
    time: Optional[int] = Field(None, ge=0)
    performance: Optional[float] = Field(None, ge=0)


# Schema trả về (response)
class TopPerformanceResponse(TopPerformanceBase):
    id: UUID
    
    model_config = ConfigDict(from_attributes=True)


# Schema cho leaderboard với thông tin user
class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    full_name: Optional[str] = None
    email: str
    score: float
    time: int
    performance: float
    lesson_id: Optional[UUID] = None
    
    model_config = ConfigDict(from_attributes=True)