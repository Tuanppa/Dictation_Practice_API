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
    
    # ==================== PHƯƠNG THỨC ADMIN MỚI ====================
    
    @staticmethod
    def get_progress_by_lesson_admin(
        db: Session,
        lesson_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Progress]:
        """
        Lấy tất cả progress của một lesson (ADMIN ONLY)
        
        Args:
            db: Database session
            lesson_id: ID của lesson
            skip: Pagination offset
            limit: Pagination limit
            
        Returns:
            List[Progress]: Danh sách progress của lesson
        """
        return db.query(Progress).filter(
            Progress.lesson_id == lesson_id
        ).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_all_progress_admin(
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[Progress]:
        """
        Lấy tất cả progress trong hệ thống (ADMIN ONLY)
        
        Args:
            db: Database session
            skip: Pagination offset
            limit: Pagination limit
            
        Returns:
            List[Progress]: Danh sách tất cả progress
        """
        return db.query(Progress).offset(skip).limit(limit).all()
    
    @staticmethod
    def admin_update_progress(
        db: Session,
        progress_id: UUID,
        progress_update: ProgressUpdate
    ) -> Progress:
        """
        Admin update toàn bộ thông tin progress (ADMIN ONLY)
        
        Args:
            db: Database session
            progress_id: ID của progress cần update
            progress_update: Data cần update
            
        Returns:
            Progress: Progress đã được update
        """
        db_progress = ProgressService.get_progress_by_id(db, progress_id)
        
        if not db_progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Progress not found"
            )
        
        # Admin có thể update tất cả các trường
        update_data = progress_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_progress, field, value)
        
        db.commit()
        db.refresh(db_progress)
        
        return db_progress
    
    # ==================== PHƯƠNG THỨC CREATE/UPDATE ====================
    
    @staticmethod
    def create_or_update_progress(
        db: Session,
        user_id: int,
        progress_data: ProgressCreate
    ) -> Progress:
        """
        Tạo mới hoặc cập nhật progress
        
        Logic:
        - CHỈ cộng score và time vào user KHI HOÀN THÀNH BÀI (completed_parts >= lesson.parts)
        - Cộng NGAY KHI hoàn thành, không đợi đến lúc làm lại
        - Trong quá trình làm bài: CHỈ update progress, KHÔNG cộng vào user
        - Khi làm lại bài (reset từ hoàn thành về 0): CHỈ reset progress, KHÔNG cộng lại điểm
        """
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
        was_completed = False
        if existing_progress:
            # Kiểm tra xem user có VỪA MỚI hoàn thành bài không
            # (chuyển từ chưa hoàn thành -> hoàn thành)
            was_completed = existing_progress.completed_parts >= lesson.parts
            is_completing_now = progress_data.completed_parts >= lesson.parts
                  
            if is_completing_now and not was_completed:
                # User VỪA MỚI hoàn thành bài -> Cộng điểm NGAY
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.score += progress_data.score
                    user.time += progress_data.time
            
        if not existing_progress or was_completed:
            # Tạo progress mới (lần đầu tiên làm bài)
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
            
            # Nếu user hoàn thành bài ngay lần đầu -> Cộng điểm
            if progress_data.completed_parts >= lesson.parts:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.score += progress_data.score
                    user.time += progress_data.time
            
            db.commit()
            db.refresh(db_progress)
            
            return db_progress
        
        # Update progress (cả trường hợp đang làm và làm lại)
        existing_progress.completed_parts = progress_data.completed_parts
        existing_progress.star_rating = progress_data.star_rating
        existing_progress.score = progress_data.score
        existing_progress.time = progress_data.time
        existing_progress.skip = progress_data.skip
        existing_progress.play_again = progress_data.play_again
        existing_progress.check = progress_data.check
            
        db.commit()
        db.refresh(existing_progress)
        return existing_progress
        
    
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
        
        # KHÔNG trừ điểm khỏi user khi xóa
        # Vì điểm đã được cộng khi hoàn thành bài
        
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