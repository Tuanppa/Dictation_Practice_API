from sqlalchemy import Integer, Float, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
import uuid
from app.core.database import Base


class Progress(Base):
    __tablename__ = "progress"
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Fields
    completed_parts: Mapped[int] = mapped_column(Integer, default=0)  # Số parts đã hoàn thành
    star_rating: Mapped[int] = mapped_column(Integer, default=0)  # 0-5 sao
    
    # Performance metrics
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Điểm số đạt được
    time: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Thời gian thực hành (giây)
    skip: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Số lần ấn skip
    play_again: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Số lần ấn nút nghe lại
    check: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Số lần ấn gợi ý
    
    # Foreign Keys
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    lesson = relationship("Lesson", back_populates="progress_records")
    
    # ❌ ĐÃ XÓA: Không còn UniqueConstraint nữa
    # Cho phép nhiều progress records cho cùng user_id và lesson_id
    # User có thể làm 1 bài nhiều lần
    
    def __repr__(self):
        return f"<Progress(id={self.id}, user_id={self.user_id}, lesson_id={self.lesson_id}, completed={self.completed_parts}, score={self.score})>"