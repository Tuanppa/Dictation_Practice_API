from sqlalchemy import String, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional
import uuid
from app.core.database import Base


class Topic(Base):
    __tablename__ = "topics"
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Fields
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[str] = mapped_column(String(50), nullable=False)  # A1, A2, B1, B2, C1, C2
    lessons_count: Mapped[int] = mapped_column(Integer, default=0)
    image_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    has_video: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # New Fields - Thêm các trường mới
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)  # Thứ tự hiển thị
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # Cho phép hiển thị
    
    # Relationships
    sections = relationship("Section", back_populates="topic", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Topic(id={self.id}, title={self.title}, level={self.level}, order={self.order_index})>"