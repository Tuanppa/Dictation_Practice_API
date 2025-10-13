from sqlalchemy import String, Integer, ForeignKey
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
    
    # Foreign Key
    topic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    topic = relationship("Topic", back_populates="sections")
    lessons = relationship("Lesson", back_populates="section", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Section(id={self.id}, title={self.title}, topic_id={self.topic_id})>"