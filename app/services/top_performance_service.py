"""
Updated Top Performance Service - Complete Implementation (FIXED)
File: app/services/top_performance_service.py

Key Features:
- Real-time incremental updates when lesson completed
- BY_LESSON mode: chỉ lưu thành tích cao nhất
- Flip modes at period end (week/month)
- Efficient ranking updates
- ALL_TIME: Query trực tiếp từ bảng users với logic score DESC, time DESC
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, case, or_
from typing import Optional, List, Any
from uuid import UUID, uuid4
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
        
        # Validate lesson_id based on mode
        if ranking.mode == RankingModeEnum.BY_LESSON:
            if not ranking.lesson_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="lesson_id is required when mode is 'by_lesson'"
                )
            lesson = db.query(Lesson).filter(Lesson.id == ranking.lesson_id).first()
            if not lesson:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Lesson not found"
                )
            final_lesson_id = ranking.lesson_id
        else:
            final_lesson_id = None
        
        db_ranking = TopPerformanceOverall(
            mode=ranking.mode,
            user_id=ranking.user_id,
            rank=ranking.rank,
            score=ranking.score,
            time=ranking.time,
            performance=ranking.performance,
            lesson_id=final_lesson_id
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
        
        **ALL_TIME**: Query trực tiếp từ bảng users
        - Sắp xếp: score DESC, time DESC
        - Logic: score cao hơn = rank cao hơn
        - Nếu score bằng nhau: time lớn hơn = chăm chỉ hơn = rank cao hơn
        
        **Các mode khác**: Query từ bảng top_performance_overall
        """
        
        # ========== ALL_TIME: Query trực tiếp từ bảng users ==========
        if mode == RankingModeEnum.ALL_TIME:
            # Query users với score > 0 (đã có hoạt động)
            users = db.query(User).filter(
                User.is_active == True,
                User.score > 0  # Chỉ lấy users đã có điểm
            ).order_by(
                desc(User.score),  # Score cao = rank cao
                desc(User.time)    # Time lớn = chăm chỉ hơn = rank cao hơn (khi score bằng nhau)
            ).limit(limit).all()
            
            leaderboard = []
            for rank, user in enumerate(users, start=1):
                leaderboard.append(LeaderboardEntry(
                    rank=rank,
                    user_id=user.id,
                    full_name=user.full_name,
                    email=user.email,
                    score=user.score,
                    time=user.time,
                    performance=user.score / user.time if user.time > 0 else 0,
                    lesson_id=None
                ))
            
            return leaderboard
        
        # ========== Các mode khác: Query từ top_performance_overall ==========
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
    
    # ==================== INCREMENTAL UPDATE - MAIN FUNCTION ====================
    
    @staticmethod
    def update_current_rankings(
        db: Session,
        user_id: int,
        score_to_add: float,
        time_to_add: int,
        lesson_id: Optional[UUID] = None
    ) -> None:
        """
        Cập nhật rankings khi user hoàn thành lesson
        
        **Xử lý 3 modes:**
        1. CURRENT_MONTH: Cộng dồn score và time
        2. CURRENT_WEEK: Cộng dồn score và time
        3. BY_LESSON: Chỉ lưu thành tích cao nhất (so sánh score, rồi time)
        
        Args:
            db: Database session
            user_id: ID của user vừa hoàn thành lesson
            score_to_add: Điểm đạt được trong lần hoàn thành này
            time_to_add: Thời gian hoàn thành (giây)
            lesson_id: ID của lesson vừa hoàn thành (bắt buộc cho BY_LESSON)
        """
        # ========== YÊU CẦU 1: Update CURRENT_MONTH ==========
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
                rank=999999,
                score=score_to_add,
                time=time_to_add,
                performance=score_to_add / time_to_add if time_to_add > 0 else 0,
                lesson_id=None
            )
            db.add(new_record)
        
        # ========== YÊU CẦU 2: Update CURRENT_WEEK ==========
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
                rank=999999,
                score=score_to_add,
                time=time_to_add,
                performance=score_to_add / time_to_add if time_to_add > 0 else 0,
                lesson_id=None
            )
            db.add(new_record)
        
        # ========== YÊU CẦU 3: Update BY_LESSON (chỉ lưu thành tích cao nhất) ==========
        if lesson_id:
            lesson_record = db.query(TopPerformanceOverall).filter(
                and_(
                    TopPerformanceOverall.user_id == user_id,
                    TopPerformanceOverall.mode == RankingModeEnum.BY_LESSON,
                    TopPerformanceOverall.lesson_id == lesson_id
                )
            ).first()
            
            if lesson_record:
                # So sánh: score cao hơn HOẶC (score bằng VÀ time nhỏ hơn = nhanh hơn)
                should_update = (
                    score_to_add > lesson_record.score or
                    (score_to_add == lesson_record.score and time_to_add < lesson_record.time)
                )
                
                if should_update:
                    lesson_record.score = score_to_add
                    lesson_record.time = time_to_add
                    lesson_record.performance = score_to_add / time_to_add if time_to_add > 0 else 0
            else:
                # Tạo record mới
                new_record = TopPerformanceOverall(
                    mode=RankingModeEnum.BY_LESSON,
                    user_id=user_id,
                    rank=999999,
                    score=score_to_add,
                    time=time_to_add,
                    performance=score_to_add / time_to_add if time_to_add > 0 else 0,
                    lesson_id=lesson_id
                )
                db.add(new_record)
        
        db.commit()
        
        # ========== Re-rank tất cả các modes ==========
        TopPerformanceService._rerank_mode(db, RankingModeEnum.CURRENT_MONTH)
        TopPerformanceService._rerank_mode(db, RankingModeEnum.CURRENT_WEEK)
        if lesson_id:
            TopPerformanceService._rerank_mode(db, RankingModeEnum.BY_LESSON, lesson_id)
    
    @staticmethod
    def _rerank_mode(
        db: Session, 
        mode: RankingModeEnum, 
        lesson_id: Optional[UUID] = None
    ) -> None:
        """
        Re-rank tất cả records trong một mode
        
        Sắp xếp theo: score DESC, time ASC (cho BY_LESSON) hoặc time DESC (cho period modes)
        """
        query = db.query(TopPerformanceOverall).filter(
            TopPerformanceOverall.mode == mode
        )
        
        if lesson_id:
            query = query.filter(TopPerformanceOverall.lesson_id == lesson_id)
        
        # Sắp xếp: score DESC, time ASC (nhanh hơn = rank cao hơn cho cùng score)
        if mode == RankingModeEnum.BY_LESSON:
            records = query.order_by(
                desc(TopPerformanceOverall.score),
                TopPerformanceOverall.time.asc()
            ).all()
        else:
            # Cho period modes: time lớn hơn = chăm chỉ hơn
            records = query.order_by(
                desc(TopPerformanceOverall.score),
                desc(TopPerformanceOverall.time)
            ).all()
        
        for new_rank, record in enumerate(records, start=1):
            record.rank = new_rank
        
        db.commit()
    
    # ==================== MODE FLIPPING ====================
    
    @staticmethod
    def flip_week_rankings(db: Session) -> dict:
        """
        YÊU CẦU 3: Flip current_week → last_week
        
        **Thời điểm chạy:** 23:59 PM Chủ Nhật (hoặc 00:00 Thứ 2)
        **Cron Schedule:** 59 23 * * 0 (23:59 Chủ Nhật)
        
        **Process:**
        1. Xóa tất cả last_week records cũ
        2. Đổi tất cả current_week → last_week
        3. current_week mới sẽ tự tạo khi user hoàn thành lesson đầu tiên
        
        Returns:
            dict với số records đã xử lý
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
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Week rankings flipped successfully"
        }
    
    @staticmethod
    def flip_month_rankings(db: Session) -> dict:
        """
        YÊU CẦU 4: Flip current_month → last_month
        
        **Thời điểm chạy:** 23:59 PM ngày cuối tháng
        **Cron Schedule:** 59 23 28-31 * * (với logic kiểm tra ngày cuối tháng)
        
        **Process:**
        1. Xóa tất cả last_month records cũ
        2. Đổi tất cả current_month → last_month
        3. current_month mới sẽ tự tạo khi user hoàn thành lesson đầu tiên
        
        Returns:
            dict với số records đã xử lý
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
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Month rankings flipped successfully"
        }
    
    # ==================== INITIAL CALCULATION (FOR MIGRATION/SETUP) ====================
    
    @staticmethod
    def calculate_and_update_rankings(
        db: Session,
        mode: RankingModeEnum,
        lesson_id: Optional[UUID] = None
    ) -> bool:
        """
        Tính toán ban đầu cho rankings (dùng khi migration hoặc khởi tạo)
        
        **Dùng cho:**
        - ALL_TIME: Tính từ users.score
        - BY_LESSON: Tính từ progress records
        - Migration ban đầu để populate current_month/current_week
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
            users = db.query(User).filter(
                User.is_active == True,
                User.score > 0
            ).order_by(
                desc(User.score),
                desc(User.time)
            ).all()
            
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
        
        # BY_LESSON: Từ progress records (lấy thành tích tốt nhất của mỗi user)
        elif mode == RankingModeEnum.BY_LESSON and lesson_id:
            # Subquery để lấy thành tích tốt nhất của mỗi user cho lesson này
            # Lấy best score cho mỗi user
            best_progress = db.query(
                Progress.user_id,
                func.max(Progress.score).label('best_score')
            ).filter(
                Progress.lesson_id == lesson_id
            ).group_by(Progress.user_id).subquery()
            
            # Join để lấy record với best score (và fastest time nếu score bằng nhau)
            progresses = db.query(Progress).join(
                best_progress,
                and_(
                    Progress.user_id == best_progress.c.user_id,
                    Progress.score == best_progress.c.best_score,
                    Progress.lesson_id == lesson_id
                )
            ).order_by(
                desc(Progress.score),
                Progress.time.asc()
            ).all()
            
            # Loại bỏ duplicates (giữ lại record với time nhỏ nhất)
            seen_users = set()
            unique_progresses = []
            for progress in progresses:
                if progress.user_id not in seen_users:
                    seen_users.add(progress.user_id)
                    unique_progresses.append(progress)
            
            for rank, progress in enumerate(unique_progresses, start=1):
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
        
        # CURRENT_MONTH/WEEK: Cho migration ban đầu
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
    ) -> Optional[Any]:
        """
        Lấy xếp hạng của một user cụ thể
        
        **ALL_TIME**: Tính rank realtime từ bảng users
        **Các mode khác**: Query từ bảng top_performance_overall
        """
        
        # ========== ALL_TIME: Tính rank realtime ==========
        if mode == RankingModeEnum.ALL_TIME:
            # Lấy thông tin user
            user = db.query(User).filter(User.id == user_id).first()
            if not user or user.score == 0:
                return None
            
            # Tính rank: đếm số users có score cao hơn, hoặc score bằng và time lớn hơn
            rank = db.query(func.count(User.id)).filter(
                and_(
                    User.is_active == True,
                    User.score > 0,
                    or_(
                        User.score > user.score,
                        and_(
                            User.score == user.score,
                            User.time > user.time
                        )
                    )
                )
            ).scalar() + 1
            
            # Tạo response object giả lập TopPerformanceOverall
            class UserRankResult:
                def __init__(self):
                    self.id = uuid4()
                    self.mode = mode
                    self.user_id = user_id
                    self.rank = rank
                    self.score = user.score
                    self.time = user.time
                    self.performance = user.score / user.time if user.time > 0 else 0
                    self.lesson_id = None
            
            return UserRankResult()
        
        # ========== Các mode khác: Query từ top_performance_overall ==========
        query = db.query(TopPerformanceOverall).filter(
            and_(
                TopPerformanceOverall.user_id == user_id,
                TopPerformanceOverall.mode == mode
            )
        )
        
        if lesson_id:
            query = query.filter(TopPerformanceOverall.lesson_id == lesson_id)
        
        return query.first()