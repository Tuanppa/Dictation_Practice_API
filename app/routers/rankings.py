from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.schemas.top_performance import (
    TopPerformanceCreate, TopPerformanceUpdate, TopPerformanceResponse,
    LeaderboardEntry, RankingMode
)
from app.services.top_performance_service import TopPerformanceService
from app.services.auth_service import get_current_user, get_current_admin_user
from app.models.user import User
from app.models.top_performance import RankingModeEnum

router = APIRouter(prefix="/rankings", tags=["Rankings & Leaderboard"])


@router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(
    mode: RankingMode = Query(..., description="Chế độ xếp hạng: all_time, monthly, weekly, by_lesson"),
    lesson_id: Optional[UUID] = Query(None, description="ID bài học (bắt buộc nếu mode=by_lesson)"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Lấy bảng xếp hạng (leaderboard)
    
    - **mode**: Chế độ xếp hạng
      - `all_time`: Xếp hạng toàn thời gian
      - `monthly`: Xếp hạng theo tháng
      - `weekly`: Xếp hạng theo tuần
      - `by_lesson`: Xếp hạng theo bài học cụ thể (cần lesson_id)
    - **lesson_id**: ID bài học (chỉ dùng cho mode=by_lesson)
    - **limit**: Số lượng người dùng trả về (mặc định 100)
    """
    # Validate lesson_id for BY_LESSON mode
    if mode == RankingMode.BY_LESSON and not lesson_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lesson_id is required when mode is by_lesson"
        )
    
    # Convert string enum to RankingModeEnum
    mode_enum = RankingModeEnum(mode.value)
    
    leaderboard = TopPerformanceService.get_leaderboard(
        db,
        mode=mode_enum,
        lesson_id=lesson_id,
        limit=limit
    )
    
    return leaderboard


@router.post("/calculate", status_code=status.HTTP_200_OK)
async def calculate_rankings(
    mode: RankingMode = Query(..., description="Chế độ xếp hạng cần tính toán"),
    lesson_id: Optional[UUID] = Query(None, description="ID bài học (bắt buộc nếu mode=by_lesson)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Tính toán và cập nhật bảng xếp hạng (chỉ admin)
    
    Endpoint này sẽ:
    1. Xóa rankings cũ cho mode đã chọn
    2. Tính toán lại rankings dựa trên dữ liệu hiện tại
    3. Lưu rankings mới vào database
    
    **Lưu ý**: Nên chạy định kỳ qua cron job
    """
    # Validate lesson_id for BY_LESSON mode
    if mode == RankingMode.BY_LESSON and not lesson_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lesson_id is required when mode is by_lesson"
        )
    
    # Convert string enum to RankingModeEnum
    mode_enum = RankingModeEnum(mode.value)
    
    success = TopPerformanceService.calculate_and_update_rankings(
        db,
        mode=mode_enum,
        lesson_id=lesson_id
    )
    
    if success:
        return {
            "message": f"Rankings calculated successfully for mode: {mode.value}",
            "mode": mode.value,
            "lesson_id": str(lesson_id) if lesson_id else None
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate rankings"
        )


@router.get("/my-rank", response_model=TopPerformanceResponse)
async def get_my_rank(
    mode: RankingMode = Query(..., description="Chế độ xếp hạng"),
    lesson_id: Optional[UUID] = Query(None, description="ID bài học (bắt buộc nếu mode=by_lesson)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy xếp hạng của user hiện tại
    
    - **mode**: Chế độ xếp hạng
    - **lesson_id**: ID bài học (chỉ dùng cho mode=by_lesson)
    """
    # Validate lesson_id for BY_LESSON mode
    if mode == RankingMode.BY_LESSON and not lesson_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lesson_id is required when mode is by_lesson"
        )
    
    # Convert string enum to RankingModeEnum
    mode_enum = RankingModeEnum(mode.value)
    
    my_rank = TopPerformanceService.get_user_rank(
        db,
        user_id=current_user.id,
        mode=mode_enum,
        lesson_id=lesson_id
    )
    
    if not my_rank:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rank not found. Rankings may need to be calculated first."
        )
    
    return my_rank


@router.get("", response_model=List[TopPerformanceResponse])
async def get_rankings(
    mode: Optional[RankingMode] = Query(None, description="Filter theo chế độ xếp hạng"),
    lesson_id: Optional[UUID] = Query(None, description="Filter theo bài học"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Lấy danh sách rankings (chỉ admin)
    
    - **mode**: Filter theo chế độ xếp hạng
    - **lesson_id**: Filter theo bài học
    - **skip**: Bỏ qua bao nhiêu records
    - **limit**: Số lượng records tối đa
    """
    # Convert string enum to RankingModeEnum if provided
    mode_enum = RankingModeEnum(mode.value) if mode else None
    
    rankings = TopPerformanceService.get_rankings(
        db,
        mode=mode_enum,
        lesson_id=lesson_id,
        skip=skip,
        limit=limit
    )
    return rankings


@router.post("", response_model=TopPerformanceResponse, status_code=status.HTTP_201_CREATED)
async def create_ranking(
    ranking: TopPerformanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Tạo ranking mới (chỉ admin)
    
    **Lưu ý**: Thường không cần tạo thủ công, sử dụng endpoint /calculate thay thế
    """
    new_ranking = TopPerformanceService.create_ranking(db, ranking)
    return new_ranking


@router.put("/{ranking_id}", response_model=TopPerformanceResponse)
async def update_ranking(
    ranking_id: UUID,
    ranking_update: TopPerformanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Cập nhật ranking (chỉ admin)
    """
    updated_ranking = TopPerformanceService.update_ranking(db, ranking_id, ranking_update)
    return updated_ranking


@router.delete("/{ranking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ranking(
    ranking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Xóa ranking (chỉ admin)
    """
    TopPerformanceService.delete_ranking(db, ranking_id)
    return None