from sqlalchemy.orm import Session
from sqlalchemy import func, desc
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
        """Lấy tất cả progress của một user (bao gồm nhiều lần làm cùng 1 lesson)"""
        return db.query(Progress).filter(
            Progress.user_id == user_id
        ).order_by(desc(Progress.created_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_progress_by_user_and_lesson(
        db: Session,
        user_id: int,
        lesson_id: UUID
    ) -> Optional[Progress]:
        """
        Lấy progress CHƯA HOÀN THÀNH gần nhất của user cho một lesson
        
        Logic:
        - Tìm progress gần nhất (order by created_at desc)
        - Trả về progress đầu tiên CHƯA hoàn thành
        - Nếu tất cả đều đã hoàn thành → trả về None (để tạo mới)
        """
        # Lấy tất cả progress của user cho lesson này, sắp xếp từ mới nhất
        all_progress = db.query(Progress).filter(
            Progress.user_id == user_id,
            Progress.lesson_id == lesson_id
        ).order_by(desc(Progress.created_at)).all()
        
        if not all_progress:
            return None
        
        # Tìm progress CHƯA hoàn thành gần nhất
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            return None
        
        for progress in all_progress:
            if progress.completed_parts < lesson.parts:
                # Tìm thấy progress chưa hoàn thành
                return progress
        
        # Tất cả progress đều đã hoàn thành → trả về None
        return None
    
    @staticmethod
    def get_all_progress_by_user_and_lesson(
        db: Session,
        user_id: int,
        lesson_id: UUID
    ) -> List[Progress]:
        """
        Lấy TẤT CẢ progress của user cho một lesson (bao gồm đã hoàn thành)
        """
        return db.query(Progress).filter(
            Progress.user_id == user_id,
            Progress.lesson_id == lesson_id
        ).order_by(desc(Progress.created_at)).all()
    
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
        Bao gồm tất cả các lần làm bài của tất cả user
        """
        return db.query(Progress).filter(
            Progress.lesson_id == lesson_id
        ).order_by(desc(Progress.created_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_all_progress_admin(
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[Progress]:
        """
        Lấy tất cả progress trong hệ thống (ADMIN ONLY)
        """
        return db.query(Progress).order_by(desc(Progress.created_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def admin_update_progress(
        db: Session,
        progress_id: UUID,
        progress_update: ProgressUpdate
    ) -> Progress:
        """
        Admin update toàn bộ thông tin progress (ADMIN ONLY)
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
    
    # ==================== PHƯƠNG THỨC CREATE/UPDATE CHÍNH ====================
    
    @staticmethod
    def create_or_update_progress(
        db: Session,
        user_id: int,
        progress_data: ProgressCreate
    ) -> Progress:
        """
        Tạo mới hoặc cập nhật progress
        
        Logic mới (cho phép làm lại bài nhiều lần):
        
        1. Nếu existing_progress TỒN TẠI và ĐÃ HOÀN THÀNH:
           → TẠO MỚI progress (bắt đầu lượt mới)
           
        2. Nếu existing_progress TỒN TẠI và CHƯA HOÀN THÀNH:
           → UPDATE progress hiện tại
           → Nếu VỪA MỚI hoàn thành → Cộng điểm vào user
           
        3. Nếu CHƯA CÓ progress:
           → TẠO MỚI progress
           → Nếu hoàn thành ngay → Cộng điểm vào user
        """
        # Verify lesson exists
        lesson = db.query(Lesson).filter(Lesson.id == progress_data.lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found"
            )
        
        # Lấy progress CHƯA hoàn thành gần nhất (nếu có)
        existing_progress = ProgressService.get_progress_by_user_and_lesson(
            db, user_id, progress_data.lesson_id
        )
        
        if existing_progress:
            # ===== CÓ PROGRESS CHƯA HOÀN THÀNH =====
            
            # Kiểm tra: VỪA MỚI hoàn thành không?
            was_completed = existing_progress.completed_parts >= lesson.parts
            is_completing_now = progress_data.completed_parts >= lesson.parts
            
            # Update progress hiện tại
            existing_progress.completed_parts = progress_data.completed_parts
            existing_progress.star_rating = progress_data.star_rating
            existing_progress.score = progress_data.score
            existing_progress.time = progress_data.time
            existing_progress.skip = progress_data.skip
            existing_progress.play_again = progress_data.play_again
            existing_progress.check = progress_data.check
            
            # Nếu VỪA MỚI hoàn thành → Cộng điểm vào user
            if is_completing_now and not was_completed:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.score += progress_data.score
                    user.time += progress_data.time
            
            db.commit()
            db.refresh(existing_progress)
            return existing_progress
            
        else:
            # ===== KHÔNG CÓ PROGRESS CHƯA HOÀN THÀNH =====
            # → TẤT CẢ progress cũ đều đã hoàn thành HOẶC chưa có progress nào
            # → TẠO MỚI progress (lượt mới)
            
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
            
            # Nếu hoàn thành ngay lần đầu → Cộng điểm
            if progress_data.completed_parts >= lesson.parts:
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
        
        # Cập nhật các trường
        update_data = progress_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_progress, field, value)
        
        db.commit()
        db.refresh(db_progress)
        
        return db_progress
    
    @staticmethod
    def delete_progress(db: Session, progress_id: UUID) -> bool:
        """Xóa progress (verify admin)"""
        db_progress = ProgressService.get_progress_by_id(db, progress_id)
        
        if not db_progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Progress not found"
            )
        
        # Verify user owns this progress
        # if db_progress.user_id != user_id:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Not authorized to delete this progress"
        #     )
        
        db.delete(db_progress)
        db.commit()
        
        return True
    
    @staticmethod
    def get_user_stats(db: Session, user_id: int) -> ProgressStats:
        """
        Lấy thống kê progress của user
        
        Note: Vì user có thể làm 1 lesson nhiều lần, 
        chỉ đếm số lessons UNIQUE đã hoàn thành ít nhất 1 lần
        """
        # Get all user progress
        user_progress = db.query(Progress).filter(Progress.user_id == user_id).all()
        
        # Calculate stats
        total_progress = len(user_progress)
        
        # Đếm unique lessons
        unique_lessons_started = set()
        unique_lessons_completed = set()
        unique_lessons_in_progress = set()
        
        total_parts = 0
        total_rating = 0
        rating_count = 0
        total_score = 0.0
        total_time = 0
        
        for progress in user_progress:
            lesson = db.query(Lesson).filter(Lesson.id == progress.lesson_id).first()
            if lesson:
                unique_lessons_started.add(lesson.id)
                
                total_parts += progress.completed_parts
                total_score += progress.score
                total_time += progress.time
                
                if progress.completed_parts >= lesson.parts:
                    unique_lessons_completed.add(lesson.id)
                elif progress.completed_parts > 0:
                    unique_lessons_in_progress.add(lesson.id)
                
                if progress.star_rating > 0:
                    total_rating += progress.star_rating
                    rating_count += 1
        
        avg_rating = total_rating / rating_count if rating_count > 0 else 0.0
        avg_score = total_score / total_progress if total_progress > 0 else 0.0
        
        return ProgressStats(
            total_lessons=len(unique_lessons_started),
            completed_lessons=len(unique_lessons_completed),
            in_progress_lessons=len(unique_lessons_in_progress),
            average_rating=round(avg_rating, 2),
            total_parts_completed=total_parts,
            total_score=round(total_score, 2),
            total_time=total_time,
            average_score=round(avg_score, 2)
        )
    
    @staticmethod
    def get_completed_lessons(db: Session, user_id: int) -> List[Progress]:
        """
        Lấy danh sách progress đã hoàn thành của user
        
        Note: Bao gồm TẤT CẢ các lần hoàn thành (user có thể hoàn thành 1 lesson nhiều lần)
        """
        progress_list = db.query(Progress).filter(
            Progress.user_id == user_id
        ).order_by(desc(Progress.created_at)).all()
        
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