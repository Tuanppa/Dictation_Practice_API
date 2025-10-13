from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.schemas.topic import TopicCreate, TopicUpdate, TopicResponse
from app.services.topic_service import TopicService
from app.services.auth_service import get_current_user, get_current_admin_user
from app.models.user import User

router = APIRouter(prefix="/topics", tags=["Topics"])


@router.get("", response_model=List[TopicResponse])
async def get_topics(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    level: Optional[str] = Query(None, description="Filter by level (A1, A2, B1, B2, C1, C2)"),
    has_video: Optional[bool] = Query(None, description="Filter by video availability"),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách topics
    
    - **skip**: Bỏ qua bao nhiêu records (pagination)
    - **limit**: Số lượng records tối đa
    - **level**: Lọc theo level
    - **has_video**: Lọc theo có video hay không
    """
    topics = TopicService.get_topics(db, skip=skip, limit=limit, level=level, has_video=has_video)
    return topics


@router.get("/search", response_model=List[TopicResponse])
async def search_topics(
    q: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Tìm kiếm topics theo title hoặc level
    """
    topics = TopicService.search_topics(db, search=q, skip=skip, limit=limit)
    return topics


@router.get("/{topic_id}", response_model=TopicResponse)
async def get_topic(
    topic_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin topic theo ID
    """
    topic = TopicService.get_topic_by_id(db, topic_id)
    
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found"
        )
    
    return topic


@router.post("", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
async def create_topic(
    topic: TopicCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Tạo topic mới (chỉ admin)
    """
    new_topic = TopicService.create_topic(db, topic)
    return new_topic


@router.put("/{topic_id}", response_model=TopicResponse)
async def update_topic(
    topic_id: UUID,
    topic_update: TopicUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Cập nhật topic (chỉ admin)
    """
    updated_topic = TopicService.update_topic(db, topic_id, topic_update)
    return updated_topic


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(
    topic_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Xóa topic (chỉ admin)
    """
    TopicService.delete_topic(db, topic_id)
    return None