from sqlalchemy import String, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from app.core.database import Base


class Section(Base):
    __tablename__ = "sections"
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Fields
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    total_lessons: Mapped[int] = mapped_column(Integer, default=0)
    
    # New Fields - Thêm các trường mới
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)  # Thứ tự hiển thị
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # Cho phép hiển thị
    
    # Foreign Key
    topic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    topic = relationship("Topic", back_populates="sections")
    lessons = relationship("Lesson", back_populates="section", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Section(id={self.id}, title={self.title}, topic_id={self.topic_id}, order={self.order_index})>"