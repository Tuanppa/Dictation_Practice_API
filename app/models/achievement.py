from sqlalchemy import String, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
import uuid
from app.core.database import Base


class Achievement(Base):
    """
    Bảng lưu các thành tích có thể đạt được
    """
    __tablename__ = "achievements"
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        index=True
    )
    
    # Fields
    name: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
        comment="Tên của thành tích"
    )
    
    score: Mapped[float] = mapped_column(
        Float, 
        default=0.0, 
        nullable=False,
        comment="Điều kiện điểm số cần đạt"
    )
    
    time: Mapped[int] = mapped_column(
        Integer, 
        default=0, 
        nullable=False,
        comment="Điều kiện thời gian cần đạt (giây)"
    )
    
    performance: Mapped[float] = mapped_column(
        Float, 
        default=0.0, 
        nullable=False,
        comment="Điều kiện hiệu suất cần đạt"
    )
    
    def __repr__(self):
        return f"<Achievement(id={self.id}, name={self.name}, score={self.score}, time={self.time}, performance={self.performance})>"