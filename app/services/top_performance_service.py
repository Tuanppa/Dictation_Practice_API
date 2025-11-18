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
        """Láº¥y ranking theo ID"""
        return db.query(TopPerformanceOverall).filter(TopPerformanceOverall.id == ranking_id).first()
    
    @staticmethod
    def get_rankings(
        db: Session,
        mode: Optional[RankingModeEnum] = None,
        lesson_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[TopPerformanceOverall]:
        """Láº¥y danh sÃ¡ch rankings vá»›i filter"""
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
        from app.schemas.top_performance import RankingMode
        
        if ranking.mode == RankingModeEnum.BY_LESSON:
            # BY_LESSON mode: lesson_id is required
            if not ranking.lesson_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="lesson_id is required when mode is 'by_lesson'"
                )
            # Verify lesson exists
            lesson = db.query(Lesson).filter(Lesson.id == ranking.lesson_id).first()
            if not lesson:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Lesson not found"
                )
            final_lesson_id = ranking.lesson_id
        else:
            # Other modes: lesson_id should be None
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
        """Cáº­p nháº­t ranking"""
        db_ranking = TopPerformanceService.get_ranking_by_id(db, ranking_id)
        
        if not db_ranking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ranking not found"
            )
        
        # Cáº­p nháº­t cÃ¡c trÆ°á»ng
        update_data = ranking_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_ranking, field, value)
        
        db.commit()
        db.refresh(db_ranking)
        
        return db_ranking
    
    @staticmethod
    def delete_ranking(db: Session, ranking_id: UUID) -> bool:
        """XÃ³a ranking"""
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
        Láº¥y báº£ng xáº¿p háº¡ng theo mode
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
        Cáº­p nháº­t rankings cho current_month vÃ  current_week khi user hoÃ n thÃ nh lesson
        
        **Real-time incremental update approach:**
        - Khi user hoÃ n thÃ nh lesson, cá»™ng dá»“n score vÃ o current_month vÃ  current_week
        - Náº¿u chÆ°a cÃ³ record â†’ Táº¡o má»›i vá»›i rank táº¡m thá»i
        - Sau Ä‘Ã³ recalculate ranks Ä‘á»ƒ Ä‘áº£m báº£o thá»© tá»± Ä‘Ãºng
        
        Args:
            db: Database session
            user_id: ID cá»§a user vá»«a hoÃ n thÃ nh lesson
            score_to_add: Äiá»ƒm cáº§n cá»™ng thÃªm
            time_to_add: Thá»i gian cáº§n cá»™ng thÃªm (giÃ¢y)
        """
        # Update CURRENT_MONTH
        current_month_record = db.query(TopPerformanceOverall).filter(
            and_(
                TopPerformanceOverall.user_id == user_id,
                TopPerformanceOverall.mode == RankingModeEnum.CURRENT_MONTH
            )
        ).first()
        
        if current_month_record:
            # Cá»™ng dá»“n score vÃ  time
            current_month_record.score += score_to_add
            current_month_record.time += time_to_add
            current_month_record.performance = (
                current_month_record.score / current_month_record.time 
                if current_month_record.time > 0 else 0
            )
        else:
            # Táº¡o record má»›i vá»›i rank táº¡m thá»i = 999999
            new_record = TopPerformanceOverall(
                mode=RankingModeEnum.CURRENT_MONTH,
                user_id=user_id,
                rank=999999,  # Táº¡m thá»i, sáº½ recalculate ngay sau
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
            # Cá»™ng dá»“n score vÃ  time
            current_week_record.score += score_to_add
            current_week_record.time += time_to_add
            current_week_record.performance = (
                current_week_record.score / current_week_record.time 
                if current_week_record.time > 0 else 0
            )
        else:
            # Táº¡o record má»›i vá»›i rank táº¡m thá»i = 999999
            new_record = TopPerformanceOverall(
                mode=RankingModeEnum.CURRENT_WEEK,
                user_id=user_id,
                rank=999999,  # Táº¡m thá»i, sáº½ recalculate ngay sau
                score=score_to_add,
                time=time_to_add,
                performance=score_to_add / time_to_add if time_to_add > 0 else 0,
                lesson_id=None
            )
            db.add(new_record)
        
        db.commit()
        
        # Recalculate ranks cho current_month vÃ  current_week
        TopPerformanceService._recalculate_ranks(db, RankingModeEnum.CURRENT_MONTH)
        TopPerformanceService._recalculate_ranks(db, RankingModeEnum.CURRENT_WEEK)
    
    @staticmethod
    def _recalculate_ranks(db: Session, mode: RankingModeEnum) -> None:
        """
        Recalculate ranks cho má»™t mode cá»¥ thá»ƒ
        
        Sáº¯p xáº¿p láº¡i ranks dá»±a trÃªn score (cao â†’ tháº¥p)
        """
        # Láº¥y táº¥t cáº£ records cá»§a mode nÃ y, sáº¯p xáº¿p theo score giáº£m dáº§n
        records = db.query(TopPerformanceOverall).filter(
            TopPerformanceOverall.mode == mode
        ).order_by(desc(TopPerformanceOverall.score)).all()
        
        # Cáº­p nháº­t rank
        for rank, record in enumerate(records, start=1):
            record.rank = rank
        
        db.commit()
    
    # ==================== MODE FLIPPING - NEW APPROACH ====================
    
    @staticmethod
    def flip_week_rankings(db: Session) -> dict:
        """
        Flip current_week â†’ last_week vÃ o Chá»§ Nháº­t 0h
        
        **Process:**
        1. XÃ³a táº¥t cáº£ last_week records cÅ©
        2. Update táº¥t cáº£ current_week â†’ last_week
        3. KhÃ´ng táº¡o current_week má»›i (sáº½ tá»± táº¡o khi user hoÃ n thÃ nh lesson Ä‘áº§u tiÃªn)
        
        **Cron Schedule:** 0 0 * * 0 (Chá»§ Nháº­t 00:00)
        
        Returns:
            dict vá»›i sá»‘ records Ä‘Ã£ flip
        """
        # 1. XÃ³a last_week cÅ©
        deleted_count = db.query(TopPerformanceOverall).filter(
            TopPerformanceOverall.mode == RankingModeEnum.LAST_WEEK
        ).delete()
        
        # 2. Flip current_week â†’ last_week
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
        Flip current_month â†’ last_month vÃ o cuá»‘i thÃ¡ng 0h
        
        **Process:**
        1. XÃ³a táº¥t cáº£ last_month records cÅ©
        2. Update táº¥t cáº£ current_month â†’ last_month
        3. KhÃ´ng táº¡o current_month má»›i (sáº½ tá»± táº¡o khi user hoÃ n thÃ nh lesson Ä‘áº§u tiÃªn)
        
        **Cron Schedule:** 
        - 0 0 L * * (Last day of month, 00:00)
        - Hoáº·c: 0 0 1 * * (NgÃ y 1 hÃ ng thÃ¡ng, 00:00) - Flip thÃ¡ng trÆ°á»›c
        
        Returns:
            dict vá»›i sá»‘ records Ä‘Ã£ flip
        """
        # 1. XÃ³a last_month cÅ©
        deleted_count = db.query(TopPerformanceOverall).filter(
            TopPerformanceOverall.mode == RankingModeEnum.LAST_MONTH
        ).delete()
        
        # 2. Flip current_month â†’ last_month
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
        TÃ­nh toÃ¡n ban Ä‘áº§u cho rankings (dÃ¹ng khi migration hoáº·c khá»Ÿi táº¡o)
        
        **Chá»‰ dÃ¹ng cho:**
        - ALL_TIME: TÃ­nh tá»« users.score
        - BY_LESSON: TÃ­nh tá»« progress records
        - Migration ban Ä‘áº§u Ä‘á»ƒ populate current_month/current_week
        
        **KhÃ´ng dÃ¹ng cho:**
        - CURRENT_MONTH/WEEK: Sáº½ tá»± Ä‘á»™ng táº¡o khi user hoÃ n thÃ nh lesson
        - LAST_MONTH/WEEK: ÄÆ°á»£c táº¡o báº±ng flip tá»« current
        """
        # XÃ³a rankings cÅ©
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
        
        # ALL_TIME: Tá»« users.score
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
        
        # BY_LESSON: Tá»« progress records
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
        
        # CURRENT_MONTH/WEEK: Chá»‰ dÃ¹ng cho migration ban Ä‘áº§u
        elif mode in [RankingModeEnum.CURRENT_MONTH, RankingModeEnum.CURRENT_WEEK]:
            # Determine time range
            if mode == RankingModeEnum.CURRENT_MONTH:
                start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:  # CURRENT_WEEK
                now = datetime.utcnow()
                start_date = now - timedelta(days=now.weekday())
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Aggregate tá»« progress
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
        """Láº¥y xáº¿p háº¡ng cá»§a má»™t user cá»¥ thá»ƒ"""
        query = db.query(TopPerformanceOverall).filter(
            and_(
                TopPerformanceOverall.user_id == user_id,
                TopPerformanceOverall.mode == mode
            )
        )
        
        if lesson_id:
            query = query.filter(TopPerformanceOverall.lesson_id == lesson_id)
        
        return query.first()