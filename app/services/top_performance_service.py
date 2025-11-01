from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
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
        
        Args:
            mode: Chế độ xếp hạng (all_time, monthly, weekly, by_lesson)
            lesson_id: ID bài học (chỉ dùng cho mode BY_LESSON)
            limit: Số lượng người dùng trả về
            
        Returns:
            Danh sách LeaderboardEntry
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
    
    @staticmethod
    def calculate_and_update_rankings(
        db: Session,
        mode: RankingModeEnum,
        lesson_id: Optional[UUID] = None
    ) -> bool:
        """
        Tính toán và cập nhật bảng xếp hạng
        
        Args:
            mode: Chế độ xếp hạng
            lesson_id: ID bài học (chỉ dùng cho mode BY_LESSON)
            
        Returns:
            True nếu thành công
        """
        # Xóa rankings cũ cho mode này
        db.query(TopPerformanceOverall).filter(
            and_(
                TopPerformanceOverall.mode == mode,
                TopPerformanceOverall.lesson_id == lesson_id if lesson_id else True
            )
        ).delete()
        
        # Lấy danh sách users và tính điểm
        if mode == RankingModeEnum.ALL_TIME:
            # Xếp hạng theo tổng điểm toàn thời gian
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
        
        elif mode == RankingModeEnum.MONTHLY:
            # Xếp hạng theo điểm trong tháng
            start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Tính tổng điểm từ progress trong tháng
            user_scores = db.query(
                Progress.user_id,
                db.func.sum(Progress.score).label('total_score'),
                db.func.sum(Progress.time).label('total_time')
            ).filter(
                Progress.updated_at >= start_of_month
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
        
        elif mode == RankingModeEnum.WEEKLY:
            # Xếp hạng theo điểm trong tuần
            start_of_week = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
            start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
            
            user_scores = db.query(
                Progress.user_id,
                db.func.sum(Progress.score).label('total_score'),
                db.func.sum(Progress.time).label('total_time')
            ).filter(
                Progress.updated_at >= start_of_week
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
        
        elif mode == RankingModeEnum.BY_LESSON and lesson_id:
            # Xếp hạng theo bài học cụ thể
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