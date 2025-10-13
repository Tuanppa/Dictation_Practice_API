from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.schemas.progress import ProgressCreate, ProgressUpdate, ProgressResponse, ProgressStats
from app.services.progress_service import ProgressService
from app.services.auth_service import get_current_user
from app.models.user import User

router = APIRouter(prefix="/progress", tags=["Progress"])


@router.get("/my", response_model=List[ProgressResponse])
async def get_my_progress(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy tất cả progress của user hiện tại
    
    - **skip**: Bỏ qua bao nhiêu records (pagination)
    - **limit**: Số lượng records tối đa
    """
    progress_list = ProgressService.get_user_progress(
        db, current_user.id, skip=skip, limit=limit
    )
    return progress_list


@router.get("/my/stats", response_model=ProgressStats)
async def get_my_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy thống kê progress của user hiện tại
    
    Returns:
    - **total_lessons**: Tổng số lessons đã bắt đầu
    - **completed_lessons**: Số lessons đã hoàn thành
    - **in_progress_lessons**: Số lessons đang học
    - **average_rating**: Đánh giá trung bình
    - **total_parts_completed**: Tổng số parts đã hoàn thành
    """
    stats = ProgressService.get_user_stats(db, current_user.id)
    return stats


@router.get("/my/completed", response_model=List[ProgressResponse])
async def get_my_completed_lessons(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy danh sách lessons đã hoàn thành của user hiện tại
    """
    completed = ProgressService.get_completed_lessons(db, current_user.id)
    return completed


@router.get("/lesson/{lesson_id}", response_model=ProgressResponse)
async def get_progress_for_lesson(
    lesson_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy progress của user hiện tại cho một lesson cụ thể
    """
    progress = ProgressService.get_progress_by_user_and_lesson(
        db, current_user.id, lesson_id
    )
    
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Progress not found for this lesson"
        )
    
    return progress


@router.post("", response_model=ProgressResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_progress(
    progress: ProgressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Tạo mới hoặc cập nhật progress của user hiện tại
    
    - Nếu progress cho lesson này đã tồn tại → cập nhật
    - Nếu chưa có → tạo mới
    
    Request body:
    - **lesson_id**: ID của lesson
    - **completed_parts**: Số parts đã hoàn thành (0 - lesson.parts)
    - **star_rating**: Đánh giá từ 0-5 sao
    """
    progress_record = ProgressService.create_or_update_progress(
        db, current_user.id, progress
    )
    return progress_record


@router.put("/{progress_id}", response_model=ProgressResponse)
async def update_progress(
    progress_id: UUID,
    progress_update: ProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cập nhật progress (chỉ cập nhật progress của chính mình)
    
    - **completed_parts**: Số parts đã hoàn thành
    - **star_rating**: Đánh giá từ 0-5 sao
    """
    updated_progress = ProgressService.update_progress(
        db, progress_id, current_user.id, progress_update
    )
    return updated_progress


@router.delete("/{progress_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_progress(
    progress_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Xóa progress (chỉ xóa progress của chính mình)
    """
    ProgressService.delete_progress(db, progress_id, current_user.id)
    return None