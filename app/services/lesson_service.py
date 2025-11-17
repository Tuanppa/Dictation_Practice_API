from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from fastapi import HTTPException, status

from app.models.lesson import Lesson
from app.models.section import Section
from Dictation_Practice_API.app.models.progress import Progress
from app.schemas.lesson import LessonCreate, LessonUpdate, LessonWithProgress


class LessonService:
    
    @staticmethod
    def get_lesson_by_id(db: Session, lesson_id: UUID) -> Optional[Lesson]:
        """Lấy lesson theo ID"""
        return db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    @staticmethod
    def get_lessons(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        section_id: Optional[UUID] = None,
        level: Optional[str] = None,
        is_premium: Optional[bool] = None,
        is_visible: Optional[bool] = True,  # Mặc định chỉ lấy lessons visible
        lesson_title: Optional[str] = None  # Thêm parameter lesson_title
    ) -> List[Lesson]:
        """Lấy danh sách lessons với filter và sắp xếp theo order_index"""
        query = db.query(Lesson)
        
        if section_id:
            query = query.filter(Lesson.section_id == section_id)
        
        if level:
            query = query.filter(Lesson.level == level)
        
        if is_premium is not None:
            query = query.filter(Lesson.is_premium == is_premium)
        
        if is_visible is not None:
            query = query.filter(Lesson.is_visible == is_visible)
        
        # Thêm filter theo title (partial match, case-insensitive)
        if lesson_title:
            query = query.filter(Lesson.title.ilike(f"%{lesson_title}%"))
        
        # Sắp xếp theo order_index
        return query.order_by(Lesson.order_index.asc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_lessons_by_section(db: Session, section_id: UUID, is_visible: bool = True) -> List[Lesson]:
        """Lấy tất cả lessons của một section theo thứ tự"""
        query = db.query(Lesson).filter(Lesson.section_id == section_id)
        
        if is_visible is not None:
            query = query.filter(Lesson.is_visible == is_visible)
        
        return query.order_by(Lesson.order_index.asc()).all()
    
    @staticmethod
    def get_all_lessons_for_admin(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        section_id: Optional[UUID] = None
    ) -> List[Lesson]:
        """Lấy tất cả lessons (bao gồm cả hidden) - cho admin"""
        query = db.query(Lesson)
        
        if section_id:
            query = query.filter(Lesson.section_id == section_id)
        
        return query.order_by(Lesson.order_index.asc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_lesson_with_progress(
        db: Session,
        lesson_id: UUID,
        user_id: int
    ) -> Optional[dict]:
        """Lấy lesson kèm progress của user"""
        lesson = LessonService.get_lesson_by_id(db, lesson_id)
        
        if not lesson:
            return None
        
        # Get user's progress for this lesson
        progress = db.query(Progress).filter(
            Progress.lesson_id == lesson_id,
            Progress.user_id == user_id
        ).first()
        
        # Return as dict (Pydantic will validate in router)
        return {
            "id": lesson.id,
            "title": lesson.title,
            "subtitle": lesson.subtitle,
            "parts": lesson.parts,
            "level": lesson.level,
            "is_premium": lesson.is_premium,
            "url_media": lesson.url_media,
            "url_script": lesson.url_script,
            "section_id": lesson.section_id,
            "order_index": lesson.order_index,
            "is_visible": lesson.is_visible,
            "completed_parts": progress.completed_parts if progress else 0,
            "star_rating": progress.star_rating if progress else 0,
            "is_completed": (progress.completed_parts >= lesson.parts) if progress else False,
            "score": progress.score if progress else 0.0,
            "time": progress.time if progress else 0
        }
    
    @staticmethod
    def create_lesson(db: Session, lesson: LessonCreate) -> Lesson:
        """Tạo lesson mới"""
        # Verify section exists
        section = db.query(Section).filter(Section.id == lesson.section_id).first()
        if not section:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Section not found"
            )
        
        db_lesson = Lesson(
            title=lesson.title,
            subtitle=lesson.subtitle,
            parts=lesson.parts,
            level=lesson.level,
            is_premium=lesson.is_premium,
            url_media=lesson.url_media,
            url_script=lesson.url_script,
            section_id=lesson.section_id,
            order_index=lesson.order_index,
            is_visible=lesson.is_visible
        )
        
        db.add(db_lesson)
        
        # Update section's total_lessons count
        section.total_lessons = db.query(Lesson).filter(
            Lesson.section_id == section.id
        ).count() + 1
        
        db.commit()
        db.refresh(db_lesson)
        
        return db_lesson
    
    @staticmethod
    def update_lesson(db: Session, lesson_id: UUID, lesson_update: LessonUpdate) -> Lesson:
        """Cập nhật lesson"""
        db_lesson = LessonService.get_lesson_by_id(db, lesson_id)
        
        if not db_lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found"
            )
        
        # Verify new section exists if changing section_id
        if lesson_update.section_id:
            section = db.query(Section).filter(Section.id == lesson_update.section_id).first()
            if not section:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Section not found"
                )
        
        # Cập nhật các trường
        update_data = lesson_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_lesson, field, value)
        
        db.commit()
        db.refresh(db_lesson)
        
        return db_lesson
    
    @staticmethod
    def reorder_lessons(db: Session, lesson_orders: List[dict]) -> bool:
        """
        Sắp xếp lại thứ tự lessons
        lesson_orders: [{"id": uuid, "order_index": int}, ...]
        """
        for item in lesson_orders:
            lesson = LessonService.get_lesson_by_id(db, item["id"])
            if lesson:
                lesson.order_index = item["order_index"]
        
        db.commit()
        return True
    
    @staticmethod
    def toggle_visibility(db: Session, lesson_id: UUID) -> Lesson:
        """Chuyển đổi trạng thái hiển thị của lesson"""
        db_lesson = LessonService.get_lesson_by_id(db, lesson_id)
        
        if not db_lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found"
            )
        
        db_lesson.is_visible = not db_lesson.is_visible
        db.commit()
        db.refresh(db_lesson)
        
        return db_lesson
    
    @staticmethod
    def delete_lesson(db: Session, lesson_id: UUID) -> bool:
        """Xóa lesson"""
        db_lesson = LessonService.get_lesson_by_id(db, lesson_id)
        
        if not db_lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found"
            )
        
        section_id = db_lesson.section_id
        
        db.delete(db_lesson)
        
        # Update section's total_lessons count
        section = db.query(Section).filter(Section.id == section_id).first()
        if section:
            section.total_lessons = db.query(Lesson).filter(
                Lesson.section_id == section_id
            ).count() - 1
        
        db.commit()
        
        return True
    
    @staticmethod
    def get_premium_lessons(db: Session, skip: int = 0, limit: int = 100) -> List[Lesson]:
        """Lấy danh sách lessons premium"""
        return db.query(Lesson).filter(
            Lesson.is_premium == True,
            Lesson.is_visible == True
        ).order_by(Lesson.order_index.asc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_free_lessons(db: Session, skip: int = 0, limit: int = 100) -> List[Lesson]:
        """Lấy danh sách lessons miễn phí"""
        return db.query(Lesson).filter(
            Lesson.is_premium == False,
            Lesson.is_visible == True
        ).order_by(Lesson.order_index.asc()).offset(skip).limit(limit).all()