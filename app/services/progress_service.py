from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from uuid import UUID
from fastapi import HTTPException, status

from app.models.progress import Progress
from app.models.lesson import Lesson
from app.models.user import User
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
            # Lưu giá trị cũ TRƯỚC KHI update
            old_score = existing_progress.score
            old_time = existing_progress.time
            
            # Update existing progress
            existing_progress.completed_parts = progress_data.completed_parts
            existing_progress.star_rating = progress_data.star_rating
            existing_progress.score = progress_data.score
            existing_progress.time = progress_data.time
            existing_progress.skip = progress_data.skip
            existing_progress.play_again = progress_data.play_again
            existing_progress.check = progress_data.check
            
            # Update user's total score and time
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                # Tính chênh lệch score và time
                score_diff = progress_data.score - old_score
                time_diff = progress_data.time - old_time
                
                user.score += score_diff
                user.time += time_diff
            
            db.commit()
            db.refresh(existing_progress)
            return existing_progress
        else:
            # Create new progress
            db_progress = Progress(
                user_id=user_id,
                lesson_id=progress_data.lesson_id,
                completed_parts=progress_data.completed_parts,
                star_rating=progress_data.star_rating,
                score=progress_data.score,
                time=progress_data.time,
                skip=progress_data.skip,
                play_again=progress_data.play_again,
                check=progress_data.check
            )
            
            db.add(db_progress)
            
            # Update user's total score and time
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.score += progress_data.score
                user.time += progress_data.time
            
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
        
        # Lưu giá trị cũ để tính chênh lệch
        old_score = db_progress.score
        old_time = db_progress.time
        
        # Cập nhật các trường
        update_data = progress_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_progress, field, value)
        
        # Update user's total score and time nếu có thay đổi
        if 'score' in update_data or 'time' in update_data:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                score_diff = db_progress.score - old_score
                time_diff = db_progress.time - old_time
                
                user.score += score_diff
                user.time += time_diff
        
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
        
        # Update user's total score and time trước khi xóa
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.score -= db_progress.score
            user.time -= db_progress.time
        
        db.delete(db_progress)
        db.commit()
        
        return True
    
    @staticmethod
    def get_user_stats(db: Session, user_id: int) -> ProgressStats:
        """Lấy thống kê progress của user"""
        # Get all user progress
        user_progress = db.query(Progress).filter(Progress.user_id == user_id).all()
        
        # Calculate stats
        total_progress = len(user_progress)
        completed_count = 0
        in_progress_count = 0
        total_parts = 0
        total_rating = 0
        rating_count = 0
        total_score = 0.0
        total_time = 0
        
        for progress in user_progress:
            lesson = db.query(Lesson).filter(Lesson.id == progress.lesson_id).first()
            if lesson:
                total_parts += progress.completed_parts
                total_score += progress.score
                total_time += progress.time
                
                if progress.completed_parts >= lesson.parts:
                    completed_count += 1
                elif progress.completed_parts > 0:
                    in_progress_count += 1
                
                if progress.star_rating > 0:
                    total_rating += progress.star_rating
                    rating_count += 1
        
        avg_rating = total_rating / rating_count if rating_count > 0 else 0.0
        avg_score = total_score / total_progress if total_progress > 0 else 0.0
        
        return ProgressStats(
            total_lessons=total_progress,
            completed_lessons=completed_count,
            in_progress_lessons=in_progress_count,
            average_rating=round(avg_rating, 2),
            total_parts_completed=total_parts,
            total_score=round(total_score, 2),
            total_time=total_time,
            average_score=round(avg_score, 2)
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
    
    @staticmethod
    def get_leaderboard(db: Session, limit: int = 100) -> List[dict]:
        """
        Lấy bảng xếp hạng top users theo score
        """
        users = db.query(User).order_by(User.score.desc()).limit(limit).all()
        
        leaderboard = []
        for rank, user in enumerate(users, 1):
            leaderboard.append({
                "rank": rank,
                "user_id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "score": user.score,
                "time": user.time
            })
        
        return leaderboard