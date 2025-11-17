"""
Updated Top Performance Service - Incremental Update Approach
File: app/services/top_performance_service.py

Key Changes:
- Real-time incremental updates when lesson completed
- Flip modes at period end instead of recalculating
- More efficient ranking updates
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, case
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from app.models.top_performance import TopPerformanceOverall, RankingModeEnum
from app.models.user import User
from app.models.lesson import Lesson
from app.models.progress import Progress
from app.schemas.top_performance import TopPerformanceCreate, TopPerformanceUpdate, LeaderboardEntry


class TopPerformanceService:
    
    @staticmethod
    def get_ranking_by_id(db: Session, ranking_id: UUID) -> Optional[TopPerformanceOverall]:
        """Lấy ranking theo ID"""
        return db.query(TopPerformanceOverall).filter(TopPerformanceOverall.id == ranking_id).first()
    
    @staticmethod
    def get_rankings(
        db: Session,
        mode: Optional[RankingModeEnum] = None,
        lesson_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[TopPerformanceOverall]:
        """Lấy danh sách rankings với filter"""
        query = db.query(TopPerformanceOverall)
        
        if mode:
            query = query.filter(TopPerformanceOverall.mode == mode)
        
        if lesson_id:
            query = query.filter(TopPerformanceOverall.lesson_id == lesson_id)
        
        return query.order_by(TopPerformanceOverall.rank.asc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def create_ranking(db: Session, ranking: TopPerformanceCreate) -> TopPerformanceOverall:
        """Tạo ranking mới"""
        # Verify user exists
        user = db.query(User).filter(User.id == ranking.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify lesson exists if lesson_id is provided
        if ranking.lesson_id:
            lesson = db.query(Lesson).filter(Lesson.id == ranking.lesson_id).first()
            if not lesson:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Lesson not found"
                )
        
        db_ranking = TopPerformanceOverall(
            mode=ranking.mode,
            user_id=ranking.user_id,
            rank=ranking.rank,
            score=ranking.score,
            time=ranking.time,
            performance=ranking.performance,
            lesson_id=ranking.lesson_id
        )
        
        db.add(db_ranking)
        db.commit()
        db.refresh(db_ranking)
        
        return db_ranking
    
    @staticmethod
    def update_ranking(
        db: Session, 
        ranking_id: UUID, 
        ranking_update: TopPerformanceUpdate
    ) -> TopPerformanceOverall:
        """Cập nhật ranking"""
        db_ranking = TopPerformanceService.get_ranking_by_id(db, ranking_id)
        
        if not db_ranking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ranking not found"
            )
        
        # Cập nhật các trường
        update_data = ranking_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_ranking, field, value)
        
        db.commit()
        db.refresh(db_ranking)
        
        return db_ranking
    
    @staticmethod
    def delete_ranking(db: Session, ranking_id: UUID) -> bool:
        """Xóa ranking"""
        db_ranking = TopPerformanceService.get_ranking_by_id(db, ranking_id)
        
        if not db_ranking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ranking not found"
            )
        
        db.delete(db_ranking)
        db.commit()
        
        return True
    
    @staticmethod
    def get_leaderboard(
        db: Session,
        mode: RankingModeEnum,
        lesson_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[LeaderboardEntry]:
        """
        Lấy bảng xếp hạng theo mode
        """
        query = db.query(
            TopPerformanceOverall,
            User.full_name,
            User.email
        ).join(User, TopPerformanceOverall.user_id == User.id)
        
        query = query.filter(TopPerformanceOverall.mode == mode)
        
        if mode == RankingModeEnum.BY_LESSON and lesson_id:
            query = query.filter(TopPerformanceOverall.lesson_id == lesson_id)
        
        results = query.order_by(TopPerformanceOverall.rank.asc()).limit(limit).all()
        
        leaderboard = []
        for ranking, full_name, email in results:
            leaderboard.append(LeaderboardEntry(
                rank=ranking.rank,
                user_id=ranking.user_id,
                full_name=full_name,
                email=email,
                score=ranking.score,
                time=ranking.time,
                performance=ranking.performance,
                lesson_id=ranking.lesson_id
            ))
        
        return leaderboard
    
    # ==================== INCREMENTAL UPDATE - NEW APPROACH ====================
    
    @staticmethod
    def update_current_rankings(
        db: Session,
        user_id: int,
        score_to_add: float,
        time_to_add: int
    ) -> None:
        """
        Cập nhật rankings cho current_month và current_week khi user hoàn thành lesson
        
        **Real-time incremental update approach:**
        - Khi user hoàn thành lesson, cộng dồn score vào current_month và current_week
        - Nếu chưa có record → Tạo mới với rank tạm thời
        - Sau đó recalculate ranks để đảm bảo thứ tự đúng
        
        Args:
            db: Database session
            user_id: ID của user vừa hoàn thành lesson
            score_to_add: Điểm cần cộng thêm
            time_to_add: Thời gian cần cộng thêm (giây)
        """
        # Update CURRENT_MONTH
        current_month_record = db.query(TopPerformanceOverall).filter(
            and_(
                TopPerformanceOverall.user_id == user_id,
                TopPerformanceOverall.mode == RankingModeEnum.CURRENT_MONTH
            )
        ).first()
        
        if current_month_record:
            # Cộng dồn score và time
            current_month_record.score += score_to_add
            current_month_record.time += time_to_add
            current_month_record.performance = (
                current_month_record.score / current_month_record.time 
                if current_month_record.time > 0 else 0
            )
        else:
            # Tạo record mới với rank tạm thời = 999999
            new_record = TopPerformanceOverall(
                mode=RankingModeEnum.CURRENT_MONTH,
                user_id=user_id,
                rank=999999,  # Tạm thời, sẽ recalculate ngay sau
                score=score_to_add,
                time=time_to_add,
                performance=score_to_add / time_to_add if time_to_add > 0 else 0,
                lesson_id=None
            )
            db.add(new_record)
        
        # Update CURRENT_WEEK
        current_week_record = db.query(TopPerformanceOverall).filter(
            and_(
                TopPerformanceOverall.user_id == user_id,
                TopPerformanceOverall.mode == RankingModeEnum.CURRENT_WEEK
            )
        ).first()
        
        if current_week_record:
            # Cộng dồn score và time
            current_week_record.score += score_to_add
            current_week_record.time += time_to_add
            current_week_record.performance = (
                current_week_record.score / current_week_record.time 
                if current_week_record.time > 0 else 0
            )
        else:
            # Tạo record mới với rank tạm thời = 999999
            new_record = TopPerformanceOverall(
                mode=RankingModeEnum.CURRENT_WEEK,
                user_id=user_id,
                rank=999999,  # Tạm thời, sẽ recalculate ngay sau
                score=score_to_add,
                time=time_to_add,
                performance=score_to_add / time_to_add if time_to_add > 0 else 0,
                lesson_id=None
            )
            db.add(new_record)
        
        db.commit()
        
        # Recalculate ranks cho current_month và current_week
        TopPerformanceService._recalculate_ranks(db, RankingModeEnum.CURRENT_MONTH)
        TopPerformanceService._recalculate_ranks(db, RankingModeEnum.CURRENT_WEEK)
    
    @staticmethod
    def _recalculate_ranks(db: Session, mode: RankingModeEnum) -> None:
        """
        Recalculate ranks cho một mode cụ thể
        
        Sắp xếp lại ranks dựa trên score (cao → thấp)
        """
        # Lấy tất cả records của mode này, sắp xếp theo score giảm dần
        records = db.query(TopPerformanceOverall).filter(
            TopPerformanceOverall.mode == mode
        ).order_by(desc(TopPerformanceOverall.score)).all()
        
        # Cập nhật rank
        for rank, record in enumerate(records, start=1):
            record.rank = rank
        
        db.commit()
    
    # ==================== MODE FLIPPING - NEW APPROACH ====================
    
    @staticmethod
    def flip_week_rankings(db: Session) -> dict:
        """
        Flip current_week → last_week vào Chủ Nhật 0h
        
        **Process:**
        1. Xóa tất cả last_week records cũ
        2. Update tất cả current_week → last_week
        3. Không tạo current_week mới (sẽ tự tạo khi user hoàn thành lesson đầu tiên)
        
        **Cron Schedule:** 0 0 * * 0 (Chủ Nhật 00:00)
        
        Returns:
            dict với số records đã flip
        """
        # 1. Xóa last_week cũ
        deleted_count = db.query(TopPerformanceOverall).filter(
            TopPerformanceOverall.mode == RankingModeEnum.LAST_WEEK
        ).delete()
        
        # 2. Flip current_week → last_week
        updated_count = db.query(TopPerformanceOverall).filter(
            TopPerformanceOverall.mode == RankingModeEnum.CURRENT_WEEK
        ).update(
            {TopPerformanceOverall.mode: RankingModeEnum.LAST_WEEK},
            synchronize_session=False
        )
        
        db.commit()
        
        return {
            "deleted_last_week": deleted_count,
            "flipped_to_last_week": updated_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def flip_month_rankings(db: Session) -> dict:
        """
        Flip current_month → last_month vào cuối tháng 0h
        
        **Process:**
        1. Xóa tất cả last_month records cũ
        2. Update tất cả current_month → last_month
        3. Không tạo current_month mới (sẽ tự tạo khi user hoàn thành lesson đầu tiên)
        
        **Cron Schedule:** 
        - 0 0 L * * (Last day of month, 00:00)
        - Hoặc: 0 0 1 * * (Ngày 1 hàng tháng, 00:00) - Flip tháng trước
        
        Returns:
            dict với số records đã flip
        """
        # 1. Xóa last_month cũ
        deleted_count = db.query(TopPerformanceOverall).filter(
            TopPerformanceOverall.mode == RankingModeEnum.LAST_MONTH
        ).delete()
        
        # 2. Flip current_month → last_month
        updated_count = db.query(TopPerformanceOverall).filter(
            TopPerformanceOverall.mode == RankingModeEnum.CURRENT_MONTH
        ).update(
            {TopPerformanceOverall.mode: RankingModeEnum.LAST_MONTH},
            synchronize_session=False
        )
        
        db.commit()
        
        return {
            "deleted_last_month": deleted_count,
            "flipped_to_last_month": updated_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # ==================== INITIAL CALCULATION (FOR MIGRATION) ====================
    
    @staticmethod
    def calculate_and_update_rankings(
        db: Session,
        mode: RankingModeEnum,
        lesson_id: Optional[UUID] = None
    ) -> bool:
        """
        Tính toán ban đầu cho rankings (dùng khi migration hoặc khởi tạo)
        
        **Chỉ dùng cho:**
        - ALL_TIME: Tính từ users.score
        - BY_LESSON: Tính từ progress records
        - Migration ban đầu để populate current_month/current_week
        
        **Không dùng cho:**
        - CURRENT_MONTH/WEEK: Sẽ tự động tạo khi user hoàn thành lesson
        - LAST_MONTH/WEEK: Được tạo bằng flip từ current
        """
        # Xóa rankings cũ
        if lesson_id:
            db.query(TopPerformanceOverall).filter(
                and_(
                    TopPerformanceOverall.mode == mode,
                    TopPerformanceOverall.lesson_id == lesson_id
                )
            ).delete()
        else:
            db.query(TopPerformanceOverall).filter(
                TopPerformanceOverall.mode == mode
            ).delete()
        
        # ALL_TIME: Từ users.score
        if mode == RankingModeEnum.ALL_TIME:
            users = db.query(User).filter(User.is_active == True).order_by(desc(User.score)).all()
            
            for rank, user in enumerate(users, start=1):
                db_ranking = TopPerformanceOverall(
                    mode=mode,
                    user_id=user.id,
                    rank=rank,
                    score=user.score,
                    time=user.time,
                    performance=user.score / user.time if user.time > 0 else 0,
                    lesson_id=None
                )
                db.add(db_ranking)
        
        # BY_LESSON: Từ progress records
        elif mode == RankingModeEnum.BY_LESSON and lesson_id:
            progresses = db.query(Progress).filter(
                Progress.lesson_id == lesson_id
            ).order_by(desc(Progress.score)).all()
            
            for rank, progress in enumerate(progresses, start=1):
                db_ranking = TopPerformanceOverall(
                    mode=mode,
                    user_id=progress.user_id,
                    rank=rank,
                    score=progress.score,
                    time=progress.time,
                    performance=progress.score / progress.time if progress.time > 0 else 0,
                    lesson_id=lesson_id
                )
                db.add(db_ranking)
        
        # CURRENT_MONTH/WEEK: Chỉ dùng cho migration ban đầu
        elif mode in [RankingModeEnum.CURRENT_MONTH, RankingModeEnum.CURRENT_WEEK]:
            # Determine time range
            if mode == RankingModeEnum.CURRENT_MONTH:
                start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:  # CURRENT_WEEK
                now = datetime.utcnow()
                start_date = now - timedelta(days=now.weekday())
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Aggregate từ progress
            user_scores = db.query(
                Progress.user_id,
                func.sum(Progress.score).label('total_score'),
                func.sum(Progress.time).label('total_time')
            ).filter(
                Progress.updated_at >= start_date
            ).group_by(Progress.user_id).order_by(desc('total_score')).all()
            
            for rank, (user_id, total_score, total_time) in enumerate(user_scores, start=1):
                db_ranking = TopPerformanceOverall(
                    mode=mode,
                    user_id=user_id,
                    rank=rank,
                    score=total_score or 0.0,
                    time=total_time or 0,
                    performance=total_score / total_time if total_time > 0 else 0,
                    lesson_id=None
                )
                db.add(db_ranking)
        
        db.commit()
        return True
    
    @staticmethod
    def get_user_rank(
        db: Session,
        user_id: int,
        mode: RankingModeEnum,
        lesson_id: Optional[UUID] = None
    ) -> Optional[TopPerformanceOverall]:
        """Lấy xếp hạng của một user cụ thể"""
        query = db.query(TopPerformanceOverall).filter(
            and_(
                TopPerformanceOverall.user_id == user_id,
                TopPerformanceOverall.mode == mode
            )
        )
        
        if lesson_id:
            query = query.filter(TopPerformanceOverall.lesson_id == lesson_id)
        
        return query.first()