from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import decode_token, create_access_token, create_refresh_token
from app.models.user import User
from app.services.user_service import UserService
from app.core.redis import get_redis

security = HTTPBearer()


class AuthService:
    
    @staticmethod
    def create_tokens(user: User) -> dict:
        """Tạo access token và refresh token"""
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        # Lưu refresh token vào Redis
        redis = get_redis()
        redis.setex(
            f"refresh_token:{user.id}",
            7 * 24 * 60 * 60,  # 7 ngày
            refresh_token
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    @staticmethod
    def verify_refresh_token(refresh_token: str, db: Session) -> Optional[User]:
        """Xác thực refresh token"""
        payload = decode_token(refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Kiểm tra refresh token trong Redis
        redis = get_redis()
        stored_token = redis.get(f"refresh_token:{user_id}")
        
        if not stored_token or stored_token != refresh_token:
            return None
        
        user = UserService.get_user_by_id(db, int(user_id))
        return user
    
    @staticmethod
    def revoke_refresh_token(user_id: int):
        """Thu hồi refresh token (logout)"""
        redis = get_redis()
        redis.delete(f"refresh_token:{user_id}")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency để lấy user hiện tại từ token"""
    token = credentials.credentials
    
    payload = decode_token(token)
    
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = UserService.get_user_by_id(db, int(user_id))
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependency để kiểm tra user đang active"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependency để kiểm tra user là admin"""
    from app.models.user import RoleEnum
    
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user