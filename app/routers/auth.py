from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import (
    UserCreate, UserLogin, Token, RefreshToken, 
    UserResponse, UserOAuthCreate
)
from app.services.user_service import UserService
from app.services.auth_service import AuthService, get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Đăng ký tài khoản mới
    
    - **email**: Email của user (unique)
    - **password**: Mật khẩu (tối thiểu 8 ký tự)
    - **full_name**: Họ tên (optional)
    """
    # Tạo user mới
    new_user = UserService.create_user(db, user)
    
    # Tạo tokens
    tokens = AuthService.create_tokens(new_user)
    
    return {
        **tokens,
        "user": new_user
    }


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Đăng nhập bằng email và password
    
    - **email**: Email đã đăng ký
    - **password**: Mật khẩu
    """
    # Xác thực user
    user = UserService.authenticate_user(
        db, 
        credentials.email, 
        credentials.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Tạo tokens
    tokens = AuthService.create_tokens(user)
    
    return {
        **tokens,
        "user": user
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh: RefreshToken,
    db: Session = Depends(get_db)
):
    """
    Làm mới access token bằng refresh token
    
    - **refresh_token**: Refresh token nhận được khi login
    """
    user = AuthService.verify_refresh_token(refresh.refresh_token, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Tạo tokens mới
    tokens = AuthService.create_tokens(user)
    
    return {
        **tokens,
        "user": user
    }


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Đăng xuất - Thu hồi refresh token
    """
    AuthService.revoke_refresh_token(current_user.id)
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Lấy thông tin user hiện tại
    """
    return current_user


@router.post("/oauth/google", response_model=Token)
async def google_login(
    user_data: UserOAuthCreate,
    db: Session = Depends(get_db)
):
    """
    Đăng nhập/Đăng ký bằng Google
    
    - **email**: Email từ Google
    - **provider_id**: Google User ID
    - **full_name**: Tên từ Google (optional)
    """
    from app.models.user import AuthProviderEnum
    
    if user_data.auth_provider != AuthProviderEnum.GOOGLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid auth provider"
        )
    
    # Tạo hoặc lấy user
    user = UserService.create_oauth_user(db, user_data)
    
    # Tạo tokens
    tokens = AuthService.create_tokens(user)
    
    return {
        **tokens,
        "user": user
    }


@router.post("/oauth/apple", response_model=Token)
async def apple_login(
    user_data: UserOAuthCreate,
    db: Session = Depends(get_db)
):
    """
    Đăng nhập/Đăng ký bằng Apple
    
    - **email**: Email từ Apple
    - **provider_id**: Apple User ID
    - **full_name**: Tên từ Apple (optional)
    """
    from app.models.user import AuthProviderEnum
    
    if user_data.auth_provider != AuthProviderEnum.APPLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid auth provider"
        )
    
    # Tạo hoặc lấy user
    user = UserService.create_oauth_user(db, user_data)
    
    # Tạo tokens
    tokens = AuthService.create_tokens(user)
    
    return {
        **tokens,
        "user": user
    }