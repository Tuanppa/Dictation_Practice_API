from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.schemas.user import (
    UserResponse, UserUpdate, UserPasswordUpdate, UserPremiumUpdate
)
from app.services.user_service import UserService
from app.services.auth_service import get_current_user, get_current_admin_user
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=List[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Lấy danh sách users (chỉ admin)
    
    - **skip**: Bỏ qua bao nhiêu records (pagination)
    - **limit**: Số lượng records tối đa
    - **search**: Tìm kiếm theo email hoặc tên
    """
    users = UserService.get_users(db, skip=skip, limit=limit, search=search)
    return users


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Lấy thông tin user hiện tại
    """
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy thông tin user theo ID
    
    - User chỉ có thể xem thông tin của chính mình
    - Admin có thể xem thông tin của bất kỳ user nào
    """
    from app.models.user import RoleEnum
    
    # Kiểm tra quyền
    if current_user.id != user_id and current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    user = UserService.get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cập nhật thông tin user hiện tại
    
    - **full_name**: Họ tên
    - **phone_number**: Số điện thoại
    - **date_of_birth**: Ngày sinh
    - **gender**: Giới tính (male/female/other)
    """
    updated_user = UserService.update_user(db, current_user.id, user_update)
    return updated_user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Cập nhật thông tin user (chỉ admin)
    """
    updated_user = UserService.update_user(db, user_id, user_update)
    return updated_user


@router.put("/me/password", response_model=UserResponse)
async def update_password(
    password_update: UserPasswordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Đổi mật khẩu
    
    - **old_password**: Mật khẩu hiện tại
    - **new_password**: Mật khẩu mới (tối thiểu 8 ký tự)
    """
    updated_user = UserService.update_password(
        db, 
        current_user.id, 
        password_update.old_password,
        password_update.new_password
    )
    return updated_user


@router.put("/{user_id}/premium", response_model=UserResponse)
async def update_premium(
    user_id: int,
    premium_update: UserPremiumUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Cập nhật premium status (chỉ admin)
    
    - **is_premium**: True/False
    - **premium_start_date**: Ngày bắt đầu premium
    - **premium_end_date**: Ngày kết thúc premium
    """
    updated_user = UserService.update_premium(db, user_id, premium_update)
    return updated_user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    hard_delete: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Xóa user (chỉ admin)
    
    - **hard_delete**: True = xóa vĩnh viễn, False = soft delete (deactivate)
    """
    if hard_delete:
        UserService.hard_delete_user(db, user_id)
        return {"message": "User deleted permanently"}
    else:
        UserService.delete_user(db, user_id)
        return {"message": "User deactivated successfully"}