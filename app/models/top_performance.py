from sqlalchemy import String, Integer, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional
import uuid
import enum
from app.core.database import Base


class RankingModeEnum(enum.Enum):
    """Các chế độ xếp hạng"""
    ALL_TIME = "all_time"  # Xếp hạng toàn thời gian
    MONTHLY = "monthly"  # Xếp hạng theo tháng
    WEEKLY = "weekly"  # Xếp hạng theo tuần
    BY_LESSON = "by_lesson"  # Xếp hạng theo bài học cụ thể


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
    mode: Mapped[RankingModeEnum] = mapped_column(
        SQLEnum(RankingModeEnum),
        nullable=False,
        index=True,
        comment="Chế độ xếp hạng: all_time, monthly, weekly, by_lesson"
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