from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional
from uuid import UUID
from enum import Enum


# Enum cho ranking mode
class RankingMode(str, Enum):
    ALL_TIME = "all_time"  # Xếp hạng toàn thời gian (từ users.score)
    LAST_MONTH = "last_month"  # Xếp hạng tháng trước (đã kết thúc) - để vinh danh
    CURRENT_MONTH = "current_month"  # Xếp hạng tháng hiện tại (đang diễn ra)
    LAST_WEEK = "last_week"  # Xếp hạng tuần trước (đã kết thúc) - để vinh danh
    CURRENT_WEEK = "current_week"  # Xếp hạng tuần hiện tại (đang diễn ra)
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
    
    @model_validator(mode='after')
    def validate_lesson_id(self):
        """
        Validate lesson_id dựa trên mode:
        - BY_LESSON: lesson_id bắt buộc
        - Các mode khác: lesson_id phải là None
        """
        if self.mode == RankingMode.BY_LESSON:
            if not self.lesson_id:
                raise ValueError("lesson_id is required when mode is 'by_lesson'")
        else:
            # Các mode khác không cần lesson_id, set None nếu có
            if self.lesson_id is not None:
                self.lesson_id = None
        
        return self


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