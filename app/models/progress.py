from sqlalchemy import Integer, ForeignKey, DateTime, UniqueConstraint
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
    
    # Foreign Keys
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lesson_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    lesson = relationship("Lesson", back_populates="progress_records")
    
    # Constraint: Mỗi user chỉ có 1 progress record cho mỗi lesson
    __table_args__ = (
        UniqueConstraint('user_id', 'lesson_id', name='unique_user_lesson_progress'),
    )
    
    def __repr__(self):
        return f"<Progress(user_id={self.user_id}, lesson_id={self.lesson_id}, completed={self.completed_parts})>"