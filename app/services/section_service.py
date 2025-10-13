from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from fastapi import HTTPException, status

from app.models.section import Section
from app.models.topic import Topic
from app.schemas.section import SectionCreate, SectionUpdate


class SectionService:
    
    @staticmethod
    def get_section_by_id(db: Session, section_id: UUID) -> Optional[Section]:
        """Lấy section theo ID"""
        return db.query(Section).filter(Section.id == section_id).first()
    
    @staticmethod
    def get_sections(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        topic_id: Optional[UUID] = None
    ) -> List[Section]:
        """Lấy danh sách sections, có thể filter theo topic_id"""
        query = db.query(Section)
        
        if topic_id:
            query = query.filter(Section.topic_id == topic_id)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def get_sections_by_topic(db: Session, topic_id: UUID) -> List[Section]:
        """Lấy tất cả sections của một topic"""
        return db.query(Section).filter(Section.topic_id == topic_id).all()
    
    @staticmethod
    def create_section(db: Session, section: SectionCreate) -> Section:
        """Tạo section mới"""
        # Verify topic exists
        topic = db.query(Topic).filter(Topic.id == section.topic_id).first()
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Topic not found"
            )
        
        db_section = Section(
            title=section.title,
            total_lessons=section.total_lessons,
            topic_id=section.topic_id
        )
        
        db.add(db_section)
        db.commit()
        db.refresh(db_section)
        
        return db_section
    
    @staticmethod
    def update_section(db: Session, section_id: UUID, section_update: SectionUpdate) -> Section:
        """Cập nhật section"""
        db_section = SectionService.get_section_by_id(db, section_id)
        
        if not db_section:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Section not found"
            )
        
        # Verify new topic exists if changing topic_id
        if section_update.topic_id:
            topic = db.query(Topic).filter(Topic.id == section_update.topic_id).first()
            if not topic:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Topic not found"
                )
        
        # Cập nhật các trường
        update_data = section_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_section, field, value)
        
        db.commit()
        db.refresh(db_section)
        
        return db_section
    
    @staticmethod
    def delete_section(db: Session, section_id: UUID) -> bool:
        """Xóa section"""
        db_section = SectionService.get_section_by_id(db, section_id)
        
        if not db_section:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Section not found"
            )
        
        db.delete(db_section)
        db.commit()
        
        return True