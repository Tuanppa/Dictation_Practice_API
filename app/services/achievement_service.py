from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from fastapi import HTTPException, status

from app.models.achievement import Achievement
from app.schemas.achievement import AchievementCreate, AchievementUpdate


class AchievementService:
    
    @staticmethod
    def get_achievement_by_id(db: Session, achievement_id: UUID) -> Optional[Achievement]:
        """Lấy achievement theo ID"""
        return db.query(Achievement).filter(Achievement.id == achievement_id).first()
    
    @staticmethod
    def get_achievements(
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[Achievement]:
        """Lấy danh sách achievements"""
        return db.query(Achievement).offset(skip).limit(limit).all()
    
    @staticmethod
    def create_achievement(db: Session, achievement: AchievementCreate) -> Achievement:
        """Tạo achievement mới"""
        db_achievement = Achievement(
            name=achievement.name,
            score=achievement.score,
            time=achievement.time,
            performance=achievement.performance
        )
        
        db.add(db_achievement)
        db.commit()
        db.refresh(db_achievement)
        
        return db_achievement
    
    @staticmethod
    def update_achievement(
        db: Session, 
        achievement_id: UUID, 
        achievement_update: AchievementUpdate
    ) -> Achievement:
        """Cập nhật achievement"""
        db_achievement = AchievementService.get_achievement_by_id(db, achievement_id)
        
        if not db_achievement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Achievement not found"
            )
        
        # Cập nhật các trường
        update_data = achievement_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_achievement, field, value)
        
        db.commit()
        db.refresh(db_achievement)
        
        return db_achievement
    
    @staticmethod
    def delete_achievement(db: Session, achievement_id: UUID) -> bool:
        """Xóa achievement"""
        db_achievement = AchievementService.get_achievement_by_id(db, achievement_id)
        
        if not db_achievement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Achievement not found"
            )
        
        db.delete(db_achievement)
        db.commit()
        
        return True
    
    @staticmethod
    def check_user_achievements(
        db: Session,
        user_score: float,
        user_time: int,
        user_performance: float
    ) -> List[Achievement]:
        """
        Kiểm tra xem user đã đạt được achievements nào
        
        Args:
            user_score: Điểm số hiện tại của user
            user_time: Thời gian học của user
            user_performance: Hiệu suất của user
            
        Returns:
            Danh sách achievements đã đạt được
        """
        achievements = db.query(Achievement).all()
        earned_achievements = []
        
        for achievement in achievements:
            # Kiểm tra xem user có đạt đủ điều kiện không
            if (user_score >= achievement.score and 
                user_time >= achievement.time and 
                user_performance >= achievement.performance):
                earned_achievements.append(achievement)
        
        return earned_achievements