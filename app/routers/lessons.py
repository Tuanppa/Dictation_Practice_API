from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.schemas.lesson import LessonCreate, LessonUpdate, LessonResponse, LessonWithProgress
from app.services.lesson_service import LessonService
from app.services.auth_service import get_current_user, get_current_admin_user
from app.models.user import User

router = APIRouter(prefix="/lessons", tags=["Lessons"])


@router.get("", response_model=List[LessonResponse])
async def get_lessons(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    section_id: Optional[UUID] = Query(None, description="Filter by section ID"),
    level: Optional[str] = Query(None, description="Filter by level"),
    is_premium: Optional[bool] = Query(None, description="Filter by premium status"),
    lesson_title: Optional[str] = Query(None, description="Search by title"),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách lessons
    
    - **skip**: Bỏ qua bao nhiêu records (pagination)
    - **limit**: Số lượng records tối đa
    - **section_id**: Lọc theo section ID
    - **level**: Lọc theo level (A1, A2, B1, B2, C1, C2)
    - **is_premium**: Lọc theo premium status
    - **lesson_title**: Tìm kiếm theo title (partial match, ví dụ: "nic" sẽ tìm thấy "a nice house")
    """
    lessons = LessonService.get_lessons(
        db, 
        skip=skip, 
        limit=limit, 
        section_id=section_id,
        level=level,
        is_premium=is_premium,
        lesson_title=lesson_title
    )
    return lessons


@router.get("/section/{section_id}", response_model=List[LessonResponse])
async def get_lessons_by_section(
    section_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Lấy tất cả lessons của một section
    """
    lessons = LessonService.get_lessons_by_section(db, section_id)
    return lessons


@router.get("/premium", response_model=List[LessonResponse])
async def get_premium_lessons(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy danh sách lessons premium (cần đăng nhập)
    """
    # Check if user has premium
    from app.models.user import User as UserModel
    user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
    
    if not user or not user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required"
        )
    
    lessons = LessonService.get_premium_lessons(db, skip=skip, limit=limit)
    return lessons


@router.get("/free", response_model=List[LessonResponse])
async def get_free_lessons(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách lessons miễn phí
    """
    lessons = LessonService.get_free_lessons(db, skip=skip, limit=limit)
    return lessons


@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    lesson_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin lesson theo ID
    """
    lesson = LessonService.get_lesson_by_id(db, lesson_id)
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    return lesson


@router.get("/{lesson_id}/with-progress", response_model=LessonWithProgress)
async def get_lesson_with_progress(
    lesson_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy lesson kèm progress của user hiện tại
    """
    lesson_with_progress = LessonService.get_lesson_with_progress(
        db, lesson_id, current_user.id
    )
    
    if not lesson_with_progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    return lesson_with_progress


@router.post("", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    lesson: LessonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Tạo lesson mới (chỉ admin)
    """
    new_lesson = LessonService.create_lesson(db, lesson)
    return new_lesson


@router.put("/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: UUID,
    lesson_update: LessonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Cập nhật lesson (chỉ admin)
    """
    updated_lesson = LessonService.update_lesson(db, lesson_id, lesson_update)
    return updated_lesson


@router.delete("/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(
    lesson_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Xóa lesson (chỉ admin)
    
    ⚠️ Cảnh báo: Xóa lesson sẽ xóa tất cả progress của lesson đó
    """
    LessonService.delete_lesson(db, lesson_id)
    return None