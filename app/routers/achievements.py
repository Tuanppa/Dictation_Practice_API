from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.schemas.achievement import AchievementCreate, AchievementUpdate, AchievementResponse
from app.services.achievement_service import AchievementService
from app.services.auth_service import get_current_user, get_current_admin_user
from app.models.user import User

router = APIRouter(prefix="/achievements", tags=["Achievements"])


@router.get("", response_model=List[AchievementResponse])
async def get_achievements(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách achievements
    
    - **skip**: Bỏ qua bao nhiêu records (pagination)
    - **limit**: Số lượng records tối đa
    """
    achievements = AchievementService.get_achievements(db, skip=skip, limit=limit)
    return achievements


@router.get("/{achievement_id}", response_model=AchievementResponse)
async def get_achievement(
    achievement_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin achievement theo ID
    """
    achievement = AchievementService.get_achievement_by_id(db, achievement_id)
    
    if not achievement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Achievement not found"
        )
    
    return achievement


@router.post("", response_model=AchievementResponse, status_code=status.HTTP_201_CREATED)
async def create_achievement(
    achievement: AchievementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Tạo achievement mới (chỉ admin)
    
    - **name**: Tên của thành tích
    - **score**: Điều kiện điểm số cần đạt
    - **time**: Điều kiện thời gian cần đạt (giây)
    - **performance**: Điều kiện hiệu suất cần đạt
    """
    new_achievement = AchievementService.create_achievement(db, achievement)
    return new_achievement


@router.put("/{achievement_id}", response_model=AchievementResponse)
async def update_achievement(
    achievement_id: UUID,
    achievement_update: AchievementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Cập nhật achievement (chỉ admin)
    """
    updated_achievement = AchievementService.update_achievement(
        db, achievement_id, achievement_update
    )
    return updated_achievement


@router.delete("/{achievement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_achievement(
    achievement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Xóa achievement (chỉ admin)
    """
    AchievementService.delete_achievement(db, achievement_id)
    return None


@router.get("/check/user", response_model=List[AchievementResponse])
async def check_user_achievements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Kiểm tra các achievements mà user hiện tại đã đạt được
    """
    earned_achievements = AchievementService.check_user_achievements(
        db,
        user_score=current_user.score,
        user_time=current_user.time,
        user_performance=current_user.score / current_user.time if current_user.time > 0 else 0
    )
    
    return earned_achievements