from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from uuid import UUID
from fastapi import HTTPException, status

from app.models.progress import Progress
from app.models.lesson import Lesson
from app.schemas.progress import ProgressCreate, ProgressUpdate, ProgressStats


class ProgressService:
    
    @staticmethod
    def get_progress_by_id(db: Session, progress_id: UUID) -> Optional[Progress]:
        """Lấy progress theo ID"""
        return db.query(Progress).filter(Progress.id == progress_id).first()
    
    @staticmethod
    def get_user_progress(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Progress]:
        """Lấy tất cả progress của một user"""
        return db.query(Progress).filter(
            Progress.user_id == user_id
        ).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_progress_by_user_and_lesson(
        db: Session,
        user_id: int,
        lesson_id: UUID
    ) -> Optional[Progress]:
        """Lấy progress của user cho một lesson cụ thể"""
        return db.query(Progress).filter(
            Progress.user_id == user_id,
            Progress.lesson_id == lesson_id
        ).first()
    
    @staticmethod
    def create_or_update_progress(
        db: Session,
        user_id: int,
        progress_data: ProgressCreate
    ) -> Progress:
        """Tạo mới hoặc cập nhật progress"""
        # Verify lesson exists
        lesson = db.query(Lesson).filter(Lesson.id == progress_data.lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found"
            )
        
        # Check if progress already exists
        existing_progress = ProgressService.get_progress_by_user_and_lesson(
            db, user_id, progress_data.lesson_id
        )
        
        if existing_progress:
            # Update existing progress
            existing_progress.completed_parts = progress_data.completed_parts
            existing_progress.star_rating = progress_data.star_rating
            
            db.commit()
            db.refresh(existing_progress)
            return existing_progress
        else:
            # Create new progress
            db_progress = Progress(
                user_id=user_id,
                lesson_id=progress_data.lesson_id,
                completed_parts=progress_data.completed_parts,
                star_rating=progress_data.star_rating
            )
            
            db.add(db_progress)
            db.commit()
            db.refresh(db_progress)
            
            return db_progress
    
    @staticmethod
    def update_progress(
        db: Session,
        progress_id: UUID,
        user_id: int,
        progress_update: ProgressUpdate
    ) -> Progress:
        """Cập nhật progress (verify user ownership)"""
        db_progress = ProgressService.get_progress_by_id(db, progress_id)
        
        if not db_progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Progress not found"
            )
        
        # Verify user owns this progress
        if db_progress.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this progress"
            )
        
        # Cập nhật các trường
        update_data = progress_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_progress, field, value)
        
        db.commit()
        db.refresh(db_progress)
        
        return db_progress
    
    @staticmethod
    def delete_progress(db: Session, progress_id: UUID, user_id: int) -> bool:
        """Xóa progress (verify user ownership)"""
        db_progress = ProgressService.get_progress_by_id(db, progress_id)
        
        if not db_progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Progress not found"
            )
        
        # Verify user owns this progress
        if db_progress.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this progress"
            )
        
        db.delete(db_progress)
        db.commit()
        
        return True
    
    @staticmethod
    def get_user_stats(db: Session, user_id: int) -> ProgressStats:
        """Lấy thống kê progress của user"""
        # Total lessons with progress
        total_progress = db.query(func.count(Progress.id)).filter(
            Progress.user_id == user_id
        ).scalar() or 0
        
        # Completed lessons (where completed_parts >= lesson.parts)
        completed_count = 0
        in_progress_count = 0
        total_parts = 0
        total_rating = 0
        rating_count = 0
        
        user_progress = db.query(Progress).filter(Progress.user_id == user_id).all()
        
        for progress in user_progress:
            lesson = db.query(Lesson).filter(Lesson.id == progress.lesson_id).first()
            if lesson:
                total_parts += progress.completed_parts
                
                if progress.completed_parts >= lesson.parts:
                    completed_count += 1
                elif progress.completed_parts > 0:
                    in_progress_count += 1
                
                if progress.star_rating > 0:
                    total_rating += progress.star_rating
                    rating_count += 1
        
        avg_rating = total_rating / rating_count if rating_count > 0 else 0.0
        
        return ProgressStats(
            total_lessons=total_progress,
            completed_lessons=completed_count,
            in_progress_lessons=in_progress_count,
            average_rating=round(avg_rating, 2),
            total_parts_completed=total_parts
        )
    
    @staticmethod
    def get_completed_lessons(db: Session, user_id: int) -> List[Progress]:
        """Lấy danh sách lessons đã hoàn thành của user"""
        progress_list = db.query(Progress).filter(Progress.user_id == user_id).all()
        
        completed = []
        for progress in progress_list:
            lesson = db.query(Lesson).filter(Lesson.id == progress.lesson_id).first()
            if lesson and progress.completed_parts >= lesson.parts:
                completed.append(progress)
        
        return completed