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
        has_video: Optional[bool] = None,
        is_visible: Optional[bool] = True  # Mặc định chỉ lấy topics visible
    ) -> List[Topic]:
        """Lấy danh sách topics với filter và sắp xếp theo order_index"""
        query = db.query(Topic)
        
        if level:
            query = query.filter(Topic.level == level)
        
        if has_video is not None:
            query = query.filter(Topic.has_video == has_video)
        
        if is_visible is not None:
            query = query.filter(Topic.is_visible == is_visible)
        
        # Sắp xếp theo order_index
        return query.order_by(Topic.order_index.asc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_all_topics_for_admin(
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[Topic]:
        """Lấy tất cả topics (bao gồm cả hidden) - cho admin"""
        return db.query(Topic).order_by(Topic.order_index.asc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def create_topic(db: Session, topic: TopicCreate) -> Topic:
        """Tạo topic mới"""
        db_topic = Topic(
            title=topic.title,
            level=topic.level,
            lessons_count=topic.lessons_count,
            image_name=topic.image_name,
            has_video=topic.has_video,
            order_index=topic.order_index,
            is_visible=topic.is_visible
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
    def reorder_topics(db: Session, topic_orders: List[dict]) -> bool:
        """
        Sắp xếp lại thứ tự topics
        topic_orders: [{"id": uuid, "order_index": int}, ...]
        """
        for item in topic_orders:
            topic = TopicService.get_topic_by_id(db, item["id"])
            if topic:
                topic.order_index = item["order_index"]
        
        db.commit()
        return True
    
    @staticmethod
    def toggle_visibility(db: Session, topic_id: UUID) -> Topic:
        """Chuyển đổi trạng thái hiển thị của topic"""
        db_topic = TopicService.get_topic_by_id(db, topic_id)
        
        if not db_topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Topic not found"
            )
        
        db_topic.is_visible = not db_topic.is_visible
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
    def search_topics(db: Session, search: str, skip: int = 0, limit: int = 100, is_visible: bool = True) -> List[Topic]:
        """Tìm kiếm topics theo title hoặc level"""
        query = db.query(Topic).filter(
            or_(
                Topic.title.ilike(f"%{search}%"),
                Topic.level.ilike(f"%{search}%")
            )
        )
        
        if is_visible is not None:
            query = query.filter(Topic.is_visible == is_visible)
        
        return query.order_by(Topic.order_index.asc()).offset(skip).limit(limit).all()