from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime, date
from typing import Optional
import enum
from app.core.database import Base


class GenderEnum(enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class RoleEnum(enum.Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class AuthProviderEnum(enum.Enum):
    EMAIL = "email"
    GOOGLE = "google"
    APPLE = "apple"


class User(Base):
    __tablename__ = "users"
    
    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Authentication
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    auth_provider: Mapped[AuthProviderEnum] = mapped_column(Enum(AuthProviderEnum), default=AuthProviderEnum.EMAIL)
    provider_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Personal Information
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[GenderEnum]] = mapped_column(Enum(GenderEnum), nullable=True)
    
    # Role & Permissions
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), default=RoleEnum.USER)
    
    # Premium Information
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    premium_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Account Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps - FIX: Dùng insert_default và onupdate đúng cách
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        insert_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        insert_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"