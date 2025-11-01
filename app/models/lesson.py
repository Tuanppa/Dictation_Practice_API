from sqlalchemy import String, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional
import uuid
from app.core.database import Base


class Lesson(Base):
    __tablename__ = "lessons"
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Fields
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtitle: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    parts: Mapped[int] = mapped_column(Integer, default=0)  # Số phần trong bài
    level: Mapped[str] = mapped_column(String(50), nullable=False)  # A1, A2, B1, B2, C1, C2
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    url_media: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # URL đến audio/video
    url_script: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # URL đến script file
    
    # New Fields - Thêm các trường mới
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)  # Thứ tự hiển thị
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # Cho phép hiển thị
    
    # Foreign Key
    section_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    section = relationship("Section", back_populates="lessons")
    progress_records = relationship("Progress", back_populates="lesson", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Lesson(id={self.id}, title={self.title}, level={self.level}, order={self.order_index})>"