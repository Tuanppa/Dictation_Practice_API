from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from fastapi import HTTPException, status

from app.models.lesson import Lesson
from app.models.section import Section
from app.models.progress import Progress
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
        is_premium: Optional[bool] = None
    ) -> List[Lesson]:
        """Lấy danh sách lessons với filter"""
        query = db.query(Lesson)
        
        if section_id:
            query = query.filter(Lesson.section_id == section_id)
        
        if level:
            query = query.filter(Lesson.level == level)
        
        if is_premium is not None:
            query = query.filter(Lesson.is_premium == is_premium)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def get_lessons_by_section(db: Session, section_id: UUID) -> List[Lesson]:
        """Lấy tất cả lessons của một section"""
        return db.query(Lesson).filter(Lesson.section_id == section_id).all()
    
    @staticmethod
    def get_lesson_with_progress(
        db: Session,
        lesson_id: UUID,
        user_id: int
    ) -> Optional[LessonWithProgress]:
        """Lấy lesson kèm progress của user"""
        lesson = LessonService.get_lesson_by_id(db, lesson_id)
        
        if not lesson:
            return None
        
        # Get user's progress for this lesson
        progress = db.query(Progress).filter(
            Progress.lesson_id == lesson_id,
            Progress.user_id == user_id
        ).first()
        
        # Convert to LessonWithProgress
        lesson_dict = {
            "id": lesson.id,
            "title": lesson.title,
            "subtitle": lesson.subtitle,
            "parts": lesson.parts,
            "level": lesson.level,
            "is_premium": lesson.is_premium,
            "url_media": lesson.url_media,
            "url_script": lesson.url_script,
            "section_id": lesson.section_id,
            "completed_parts": progress.completed_parts if progress else 0,
            "star_rating": progress.star_rating if progress else 0,
            "is_completed": (progress.completed_parts >= lesson.parts) if progress else False
        }
        
        return LessonWithProgress(**lesson_dict)
    
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
            section_id=lesson.section_id
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
            Lesson.is_premium == True
        ).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_free_lessons(db: Session, skip: int = 0, limit: int = 100) -> List[Lesson]:
        """Lấy danh sách lessons miễn phí"""
        return db.query(Lesson).filter(
            Lesson.is_premium == False
        ).offset(skip).limit(limit).all()