"""
Models package
Import tất cả models để SQLAlchemy có thể tạo tables
"""
from app.models.user import User
from app.models.topic import Topic
from app.models.section import Section
from app.models.lesson import Lesson
from app.models.progress import Progress
from app.models.top_performance import TopPerformanceOverall
from app.models.achievement import Achievement

__all__ = [
    "User",
    "Topic",
    "Section",
    "Lesson",
    "Progress",
    "Achievement",
    "TopPerformanceOverall"
]