"""
Fixed Top Performance Model - Correct Enum Handling
File: app/models/top_performance.py

FIX: Use values_callable to send lowercase enum values to PostgreSQL
"""

from sqlalchemy import String, Integer, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator
from typing import Optional
import uuid
import enum
from app.core.database import Base


class RankingModeEnum(enum.Enum):
    """Các chế độ xếp hạng"""
    ALL_TIME = "all_time"
    LAST_MONTH = "last_month"
    CURRENT_MONTH = "current_month"
    LAST_WEEK = "last_week"
    CURRENT_WEEK = "current_week"
    BY_LESSON = "by_lesson"


class RankingModeType(TypeDecorator):
    """
    Custom TypeDecorator để handle RankingModeEnum với lowercase values trong PostgreSQL.
    
    Giải quyết vấn đề SQLAlchemy sử dụng enum.name (UPPERCASE) thay vì enum.value (lowercase)
    khi binding parameters.
    """
    impl = SQLEnum(
        'all_time', 'last_month', 'current_month', 
        'last_week', 'current_week', 'by_lesson',
        name='rankingmodeenum',
        create_type=False  # Không tạo type mới vì đã có từ migration
    )
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        """Convert Python enum sang database value (lowercase)"""
        if value is not None:
            if isinstance(value, RankingModeEnum):
                return value.value  # Trả về 'all_time' thay vì 'ALL_TIME'
            return value
        return value
    
    def process_result_value(self, value, dialect):
        """Convert database value sang Python enum"""
        if value is not None:
            return RankingModeEnum(value)
        return value


class TopPerformanceOverall(Base):
    """
    Bảng lưu bảng xếp hạng thành tích người dùng
    """
    __tablename__ = "top_performance_overall"
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        index=True
    )
    
    # Mode - Chế độ xếp hạng
    # FIX: Sử dụng TypeDecorator để convert enum values đúng cách
    mode: Mapped[RankingModeEnum] = mapped_column(
        RankingModeType(),
        nullable=False,
        index=True,
        comment="Chế độ xếp hạng: all_time, last_month, current_month, last_week, current_week, by_lesson"
    )
    
    # Foreign Key - User
    user_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Rank - Thứ tự xếp hạng
    rank: Mapped[int] = mapped_column(
        Integer, 
        nullable=False,
        comment="Thứ tự xếp hạng"
    )
    
    # Performance metrics
    score: Mapped[float] = mapped_column(
        Float, 
        default=0.0, 
        nullable=False,
        comment="Điểm số đạt được"
    )
    
    time: Mapped[int] = mapped_column(
        Integer, 
        default=0, 
        nullable=False,
        comment="Thời gian thực hành (giây)"
    )
    
    performance: Mapped[float] = mapped_column(
        Float, 
        default=0.0, 
        nullable=False,
        comment="Hiệu suất tổng thể"
    )
    
    # Foreign Key - Lesson (chỉ dùng cho mode BY_LESSON)
    lesson_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lessons.id", ondelete="CASCADE"), 
        nullable=True,
        index=True,
        comment="ID bài học (chỉ dùng cho chế độ xếp hạng theo bài)"
    )
    
    # Relationships
    user = relationship("User")
    lesson = relationship("Lesson")
    
    def __repr__(self):
        return f"<TopPerformanceOverall(mode={self.mode.value}, user_id={self.user_id}, rank={self.rank}, score={self.score})>"