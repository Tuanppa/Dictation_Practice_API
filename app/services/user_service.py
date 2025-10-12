from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from datetime import datetime
from fastapi import HTTPException, status

from app.models.user import User, AuthProviderEnum
from app.schemas.user import UserCreate, UserUpdate, UserOAuthCreate, UserPremiumUpdate
from app.core.security import get_password_hash, verify_password
from app.core.redis import get_redis


class UserService:
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Lấy user theo ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Lấy user theo email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_users(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[User]:
        """Lấy danh sách users với phân trang và tìm kiếm"""
        query = db.query(User)
        
        if search:
            query = query.filter(
                or_(
                    User.email.ilike(f"%{search}%"),
                    User.full_name.ilike(f"%{search}%")
                )
            )
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:
        """Tạo user mới"""
        # Kiểm tra email đã tồn tại
        existing_user = UserService.get_user_by_email(db, user.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Tạo user mới
        hashed_password = get_password_hash(user.password)
        db_user = User(
            email=user.email,
            hashed_password=hashed_password,
            full_name=user.full_name,
            phone_number=user.phone_number,
            date_of_birth=user.date_of_birth,
            gender=user.gender,
            auth_provider=AuthProviderEnum.EMAIL
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    def create_oauth_user(db: Session, user: UserOAuthCreate) -> User:
        """Tạo hoặc lấy user từ OAuth (Google/Apple)"""
        # Kiểm tra user đã tồn tại
        existing_user = db.query(User).filter(
            User.email == user.email,
            User.auth_provider == user.auth_provider
        ).first()
        
        if existing_user:
            # Cập nhật last_login
            existing_user.last_login = datetime.utcnow()
            db.commit()
            db.refresh(existing_user)
            return existing_user
        
        # Tạo user mới
        db_user = User(
            email=user.email,
            full_name=user.full_name,
            auth_provider=user.auth_provider,
            provider_id=user.provider_id,
            is_verified=True,  # OAuth users are auto-verified
            last_login=datetime.utcnow()
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """Xác thực user"""
        user = UserService.get_user_by_email(db, email)
        
        if not user:
            return None
        
        if user.auth_provider != AuthProviderEnum.EMAIL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Please login with {user.auth_provider.value}"
            )
        
        # Kiểm tra hashed_password không None
        if not user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has no password set"
            )
        
        if not verify_password(password, user.hashed_password):
            return None
        
        # Cập nhật last_login
        user.last_login = datetime.utcnow()
        db.commit()
        
        return user
    
    @staticmethod
    def update_user(db: Session, user_id: int, user_update: UserUpdate) -> User:
        """Cập nhật thông tin user"""
        db_user = UserService.get_user_by_id(db, user_id)
        
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Cập nhật các trường
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    def update_password(db: Session, user_id: int, old_password: str, new_password: str) -> User:
        """Cập nhật password"""
        db_user = UserService.get_user_by_id(db, user_id)
        
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if db_user.auth_provider != AuthProviderEnum.EMAIL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change password for OAuth accounts"
            )
        
        # Kiểm tra hashed_password không None
        if not db_user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has no password set"
            )
        
        # Xác thực password cũ
        if not verify_password(old_password, db_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password"
            )
        
        # Cập nhật password mới
        db_user.hashed_password = get_password_hash(new_password)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    def update_premium(db: Session, user_id: int, premium_update: UserPremiumUpdate) -> User:
        """Cập nhật premium status"""
        db_user = UserService.get_user_by_id(db, user_id)
        
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        db_user.is_premium = premium_update.is_premium
        db_user.premium_start_date = premium_update.premium_start_date
        db_user.premium_end_date = premium_update.premium_end_date
        
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        """Xóa user (soft delete)"""
        db_user = UserService.get_user_by_id(db, user_id)
        
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Soft delete: deactivate user
        db_user.is_active = False
        db.commit()
        
        # Xóa cache nếu có
        redis = get_redis()
        redis.delete(f"user:{user_id}")
        
        return True
    
    @staticmethod
    def hard_delete_user(db: Session, user_id: int) -> bool:
        """Xóa user vĩnh viễn (hard delete)"""
        db_user = UserService.get_user_by_id(db, user_id)
        
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        db.delete(db_user)
        db.commit()
        
        # Xóa cache
        redis = get_redis()
        redis.delete(f"user:{user_id}")
        
        return True