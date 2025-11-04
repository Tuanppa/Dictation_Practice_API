"""
User Service with Avatar Support
File: app/services/user_service.py
Railway + Cloudinary Ready

Key Changes:
- Added avatar_url to create_user()
- Added avatar_url to create_oauth_user()
- Added update_avatar() method
- Added update_avatar_from_file() method
- Added avatar_url to get_user_stats()
"""

from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import HTTPException, status, UploadFile

from app.models.user import User, AuthProviderEnum
from app.schemas.user import (
    UserCreate, UserUpdate, UserOAuthCreate, UserPremiumUpdate, 
    UserAchievementsUpdate, UserStats, UserAvatarUpdate
)
from app.core.security import get_password_hash, verify_password
from app.core.redis import get_redis
from app.models.progress import Progress


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
        existing_user = UserService.get_user_by_email(db, user.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        hashed_password = get_password_hash(user.password)
        db_user = User(
            email=user.email,
            hashed_password=hashed_password,
            full_name=user.full_name,
            phone_number=user.phone_number,
            date_of_birth=user.date_of_birth,
            gender=user.gender,
            avatar_url=user.avatar_url,
            auth_provider=AuthProviderEnum.EMAIL,
            score=0.0,
            time=0,
            achievements={}
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    def create_oauth_user(db: Session, user: UserOAuthCreate) -> User:
        """Tạo hoặc lấy user từ OAuth (Google/Apple)"""
        existing_user = db.query(User).filter(
            User.email == user.email,
            User.auth_provider == user.auth_provider
        ).first()
        
        if existing_user:
            existing_user.last_login = datetime.utcnow()
            # Update avatar if provided and user doesn't have one
            if user.avatar_url and not existing_user.avatar_url:
                existing_user.avatar_url = user.avatar_url
            db.commit()
            db.refresh(existing_user)
            return existing_user
        
        db_user = User(
            email=user.email,
            full_name=user.full_name,
            auth_provider=user.auth_provider,
            provider_id=user.provider_id,
            avatar_url=user.avatar_url,
            is_verified=True,
            last_login=datetime.utcnow(),
            score=0.0,
            time=0,
            achievements={}
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
        
        if not user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has no password set"
            )
        
        if not verify_password(password, user.hashed_password):
            return None
        
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
        
        if not db_user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has no password set"
            )
        
        if not verify_password(old_password, db_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password"
            )
        
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
    
    # ==================== AVATAR METHODS ====================
    
    @staticmethod
    def update_avatar(db: Session, user_id: int, avatar_update: UserAvatarUpdate) -> User:
        """
        Cập nhật avatar từ URL (dùng khi có sẵn Cloudinary URL)
        
        Args:
            db: Database session
            user_id: ID của user
            avatar_update: Cloudinary avatar URL mới
            
        Returns:
            User đã được cập nhật
        """
        db_user = UserService.get_user_by_id(db, user_id)
        
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        old_avatar = db_user.avatar_url
        db_user.avatar_url = avatar_update.avatar_url
        
        db.commit()
        db.refresh(db_user)
        
        # Optional: Delete old avatar from Cloudinary (async)
        if old_avatar and old_avatar != avatar_update.avatar_url:
            try:
                from app.utils.cloudinary_upload import CloudinaryUploadService
                import asyncio
                asyncio.create_task(CloudinaryUploadService.delete_avatar(old_avatar))
            except Exception as e:
                print(f"Warning: Could not delete old avatar: {e}")
        
        return db_user
    
    @staticmethod
    async def update_avatar_from_file(
        db: Session, 
        user_id: int, 
        file: UploadFile
    ) -> User:
        """
        Upload avatar file lên Cloudinary và cập nhật vào database
        
        Args:
            db: Database session
            user_id: ID của user
            file: File avatar cần upload
            
        Returns:
            User đã được cập nhật với avatar URL mới
        """
        from app.utils.cloudinary_upload import CloudinaryUploadService
        
        db_user = UserService.get_user_by_id(db, user_id)
        
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        old_avatar = db_user.avatar_url
        
        # Upload to Cloudinary
        avatar_url = await CloudinaryUploadService.upload_avatar(file, user_id)
        
        # Update database
        db_user.avatar_url = avatar_url
        db.commit()
        db.refresh(db_user)
        
        # Delete old avatar (optional, để tiết kiệm storage)
        if old_avatar and old_avatar != avatar_url:
            await CloudinaryUploadService.delete_avatar(old_avatar)
        
        return db_user
    
    # ==================== OTHER METHODS ====================
    
    @staticmethod
    def update_achievements(db: Session, user_id: int, achievements_update: UserAchievementsUpdate) -> User:
        """Cập nhật achievements của user"""
        db_user = UserService.get_user_by_id(db, user_id)
        
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if db_user.achievements:
            db_user.achievements.update(achievements_update.achievements)
        else:
            db_user.achievements = achievements_update.achievements
        
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    def add_achievement(db: Session, user_id: int, achievement_key: str, achievement_data: Dict[str, Any]) -> User:
        """Thêm một achievement mới cho user"""
        db_user = UserService.get_user_by_id(db, user_id)
        
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not db_user.achievements:
            db_user.achievements = {}
        
        db_user.achievements[achievement_key] = achievement_data
        
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    def get_user_stats(db: Session, user_id: int) -> UserStats:
        """Lấy thống kê chi tiết của user"""
        db_user = UserService.get_user_by_id(db, user_id)
        
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        progress_records = db.query(Progress).filter(Progress.user_id == user_id).all()
        
        completed_count = 0
        in_progress_count = 0
        total_rating = 0
        rating_count = 0
        
        for progress in progress_records:
            from app.models.lesson import Lesson
            lesson = db.query(Lesson).filter(Lesson.id == progress.lesson_id).first()
            if lesson:
                if progress.completed_parts >= lesson.parts:
                    completed_count += 1
                elif progress.completed_parts > 0:
                    in_progress_count += 1
                
                if progress.star_rating > 0:
                    total_rating += progress.star_rating
                    rating_count += 1
        
        avg_rating = total_rating / rating_count if rating_count > 0 else 0.0
        achievements_count = len(db_user.achievements) if db_user.achievements else 0
        
        return UserStats(
            user_id=db_user.id,
            total_score=db_user.score,
            total_time=db_user.time,
            total_lessons_completed=completed_count,
            total_lessons_in_progress=in_progress_count,
            average_rating=round(avg_rating, 2),
            achievements_count=achievements_count,
            achievements=db_user.achievements,
            avatar_url=db_user.avatar_url
        )
    
    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        """Xóa user (soft delete)"""
        db_user = UserService.get_user_by_id(db, user_id)
        
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        db_user.is_active = False
        db.commit()
        
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
        
        redis = get_redis()
        redis.delete(f"user:{user_id}")
        
        return True