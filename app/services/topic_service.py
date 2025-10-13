from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from uuid import UUID
from fastapi import HTTPException, status

from app.models.topic import Topic
from app.schemas.topic import TopicCreate, TopicUpdate


class TopicService:
    
    @staticmethod
    def get_topic_by_id(db: Session, topic_id: UUID) -> Optional[Topic]:
        """Lấy topic theo ID"""
        return db.query(Topic).filter(Topic.id == topic_id).first()
    
    @staticmethod
    def get_topics(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        level: Optional[str] = None,
        has_video: Optional[bool] = None
    ) -> List[Topic]:
        """Lấy danh sách topics với filter"""
        query = db.query(Topic)
        
        if level:
            query = query.filter(Topic.level == level)
        
        if has_video is not None:
            query = query.filter(Topic.has_video == has_video)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def create_topic(db: Session, topic: TopicCreate) -> Topic:
        """Tạo topic mới"""
        db_topic = Topic(
            title=topic.title,
            level=topic.level,
            lessons_count=topic.lessons_count,
            image_name=topic.image_name,
            has_video=topic.has_video
        )
        
        db.add(db_topic)
        db.commit()
        db.refresh(db_topic)
        
        return db_topic
    
    @staticmethod
    def update_topic(db: Session, topic_id: UUID, topic_update: TopicUpdate) -> Topic:
        """Cập nhật topic"""
        db_topic = TopicService.get_topic_by_id(db, topic_id)
        
        if not db_topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Topic not found"
            )
        
        # Cập nhật các trường
        update_data = topic_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_topic, field, value)
        
        db.commit()
        db.refresh(db_topic)
        
        return db_topic
    
    @staticmethod
    def delete_topic(db: Session, topic_id: UUID) -> bool:
        """Xóa topic"""
        db_topic = TopicService.get_topic_by_id(db, topic_id)
        
        if not db_topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Topic not found"
            )
        
        db.delete(db_topic)
        db.commit()
        
        return True
    
    @staticmethod
    def search_topics(db: Session, search: str, skip: int = 0, limit: int = 100) -> List[Topic]:
        """Tìm kiếm topics theo title hoặc level"""
        return db.query(Topic).filter(
            or_(
                Topic.title.ilike(f"%{search}%"),
                Topic.level.ilike(f"%{search}%")
            )
        ).offset(skip).limit(limit).all()