"""
Updated Rankings Router - Với Mode Flipping Endpoints
File: app/routers/rankings.py

Key Changes:
- Added POST /rankings/flip-week - Flip current_week → last_week
- Added POST /rankings/flip-month - Flip current_month → last_month
- Removed calculate endpoints for current periods (auto-update now)
"""

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
    mode: RankingMode = Query(..., description="Chế độ xếp hạng"),
    lesson_id: Optional[UUID] = Query(None, description="ID bài học (bắt buộc nếu mode=by_lesson)"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Lấy bảng xếp hạng (leaderboard)
    
    ## Các chế độ xếp hạng:
    
    - **all_time**: Xếp hạng toàn thời gian (từ users.score tích lũy)
      - Data source: users.score field
      
    - **last_month**: Xếp hạng tháng trước (đã kết thúc) 🏆
      - Use case: Hall of Fame - Vinh danh winners tháng trước
      - Read-only: Được tạo bằng cách flip từ current_month
      
    - **current_month**: Xếp hạng tháng hiện tại (đang diễn ra) 📈
      - Use case: Live leaderboard tháng này
      - Auto-update: Tự động cập nhật khi user hoàn thành lesson
      
    - **last_week**: Xếp hạng tuần trước (đã kết thúc) 🏆
      - Use case: Hall of Fame - Vinh danh winners tuần trước
      - Read-only: Được tạo bằng cách flip từ current_week
      
    - **current_week**: Xếp hạng tuần hiện tại (đang diễn ra) 📈
      - Use case: Live leaderboard tuần này
      - Auto-update: Tự động cập nhật khi user hoàn thành lesson
      
    - **by_lesson**: Xếp hạng theo bài học cụ thể
      - Use case: Top performers cho một bài học
      - Requires: lesson_id parameter
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


# ==================== MODE FLIPPING ENDPOINTS (CRON JOBS) ====================

@router.post("/flip-week", status_code=status.HTTP_200_OK)
async def flip_week_rankings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Flip current_week → last_week (Chủ Nhật 0h)
    
    **Cron Schedule:** `0 0 * * 0` (Chủ Nhật 00:00)
    
    **Process:**
    1. Xóa tất cả last_week cũ
    2. Đổi tất cả current_week → last_week
    3. current_week mới sẽ tự tạo khi user hoàn thành lesson đầu tiên
    
    **Example cURL:**
    ```bash
    curl -X POST "https://your-api.railway.app/api/v1/rankings/flip-week" \\
      -H "Authorization: Bearer $ADMIN_TOKEN"
    ```
    
    **Example Railway Cron:**
    ```toml
    [[crons]]
    schedule = "0 0 * * 0"
    command = "curl -X POST $API_URL/rankings/flip-week -H 'Authorization: Bearer $ADMIN_TOKEN'"
    ```
    """
    result = TopPerformanceService.flip_week_rankings(db)
    
    return {
        "message": "Week rankings flipped successfully",
        "details": result
    }


@router.post("/flip-month", status_code=status.HTTP_200_OK)
async def flip_month_rankings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Flip current_month → last_month (Ngày 1 hàng tháng 0h)
    
    **Cron Schedule:** `0 0 1 * *` (Ngày 1 hàng tháng, 00:00)
    
    **Process:**
    1. Xóa tất cả last_month cũ
    2. Đổi tất cả current_month → last_month
    3. current_month mới sẽ tự tạo khi user hoàn thành lesson đầu tiên
    
    **Example cURL:**
    ```bash
    curl -X POST "https://your-api.railway.app/api/v1/rankings/flip-month" \\
      -H "Authorization: Bearer $ADMIN_TOKEN"
    ```
    
    **Example Railway Cron:**
    ```toml
    [[crons]]
    schedule = "0 0 1 * *"
    command = "curl -X POST $API_URL/rankings/flip-month -H 'Authorization: Bearer $ADMIN_TOKEN'"
    ```
    """
    result = TopPerformanceService.flip_month_rankings(db)
    
    return {
        "message": "Month rankings flipped successfully",
        "details": result
    }


# ==================== INITIAL CALCULATION (MIGRATION ONLY) ====================

@router.post("/calculate", status_code=status.HTTP_200_OK)
async def calculate_rankings(
    mode: RankingMode = Query(..., description="Chế độ xếp hạng cần tính toán"),
    lesson_id: Optional[UUID] = Query(None, description="ID bài học (bắt buộc nếu mode=by_lesson)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Tính toán rankings ban đầu (CHỈ DÙNG KHI MIGRATION hoặc KHỞI TẠO)
    
    **Use cases:**
    - `all_time`: Tính từ users.score
    - `current_month`: Populate ban đầu từ progress records (sau đó auto-update)
    - `current_week`: Populate ban đầu từ progress records (sau đó auto-update)
    - `by_lesson`: Tính từ progress records
    
    **KHÔNG dùng cho:**
    - `last_month`: Dùng /flip-month thay thế
    - `last_week`: Dùng /flip-week thay thế
    
    **Note:** Sau khi migrate, current_month/current_week sẽ tự động update khi user hoàn thành lesson.
    Endpoint này CHỈ cần chạy 1 lần khi setup ban đầu.
    """
    # Validate
    if mode == RankingMode.BY_LESSON and not lesson_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lesson_id is required when mode is by_lesson"
        )
    
    # Warning cho last_month/last_week
    if mode in [RankingMode.LAST_MONTH, RankingMode.LAST_WEEK]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Use /flip-month or /flip-week endpoint instead of calculating {mode.value}"
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
            "lesson_id": str(lesson_id) if lesson_id else None,
            "note": "After this initial calculation, current_month/current_week will auto-update when users complete lessons"
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate rankings"
        )


# ==================== USER ENDPOINTS ====================

@router.get("/my-rank", response_model=TopPerformanceResponse)
async def get_my_rank(
    mode: RankingMode = Query(..., description="Chế độ xếp hạng"),
    lesson_id: Optional[UUID] = Query(None, description="ID bài học (bắt buộc nếu mode=by_lesson)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy xếp hạng của user hiện tại
    
    **Examples:**
    ```
    # My all-time rank
    GET /rankings/my-rank?mode=all_time
    
    # My rank this month
    GET /rankings/my-rank?mode=current_month
    
    # My rank this week
    GET /rankings/my-rank?mode=current_week
    
    # My rank for a specific lesson
    GET /rankings/my-rank?mode=by_lesson&lesson_id=abc-123
    ```
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
            detail=f"Rank not found for {mode.value}. You may not have completed any lessons this period."
        )
    
    return my_rank


# ==================== ADMIN ENDPOINTS ====================

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
    
    **Lưu ý**: Không nên tạo thủ công. Rankings sẽ tự động tạo khi user hoàn thành lesson.
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