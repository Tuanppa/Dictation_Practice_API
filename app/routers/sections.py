from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.schemas.section import SectionCreate, SectionUpdate, SectionResponse
from app.services.section_service import SectionService
from app.services.auth_service import get_current_user, get_current_admin_user
from app.models.user import User

router = APIRouter(prefix="/sections", tags=["Sections"])


@router.get("", response_model=List[SectionResponse])
async def get_sections(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    topic_id: Optional[UUID] = Query(None, description="Filter by topic ID"),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách sections
    
    - **skip**: Bỏ qua bao nhiêu records (pagination)
    - **limit**: Số lượng records tối đa
    - **topic_id**: Lọc theo topic ID
    """
    sections = SectionService.get_sections(db, skip=skip, limit=limit, topic_id=topic_id)
    return sections


@router.get("/topic/{topic_id}", response_model=List[SectionResponse])
async def get_sections_by_topic(
    topic_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Lấy tất cả sections của một topic
    """
    sections = SectionService.get_sections_by_topic(db, topic_id)
    return sections


@router.get("/{section_id}", response_model=SectionResponse)
async def get_section(
    section_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin section theo ID
    """
    section = SectionService.get_section_by_id(db, section_id)
    
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found"
        )
    
    return section


@router.post("", response_model=SectionResponse, status_code=status.HTTP_201_CREATED)
async def create_section(
    section: SectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Tạo section mới (chỉ admin)
    
    - **title**: Tên section
    - **total_lessons**: Tổng số lessons
    - **topic_id**: ID của topic
    """
    new_section = SectionService.create_section(db, section)
    return new_section


@router.put("/{section_id}", response_model=SectionResponse)
async def update_section(
    section_id: UUID,
    section_update: SectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Cập nhật section (chỉ admin)
    """
    updated_section = SectionService.update_section(db, section_id, section_update)
    return updated_section


@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(
    section_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Xóa section (chỉ admin)
    
    ⚠️ Cảnh báo: Xóa section sẽ xóa tất cả lessons trong section đó
    """
    SectionService.delete_section(db, section_id)
    return None