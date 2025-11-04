"""
Users Router with Avatar Endpoints
File: app/routers/users.py
Railway + Cloudinary Ready

New Endpoints:
- PUT /users/me/avatar - Upload avatar file
- PUT /users/me/avatar/url - Update avatar from URL
- DELETE /users/me/avatar - Delete avatar
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.schemas.user import (
    UserResponse, UserUpdate, UserPasswordUpdate, UserPremiumUpdate, UserAvatarUpdate
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
    Lấy thông tin user hiện tại (bao gồm avatar_url)
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
    - **avatar_url**: URL avatar (optional, hoặc dùng endpoint upload)
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


# ==================== AVATAR ENDPOINTS ====================

@router.put("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(
        ..., 
        description="Avatar image file (max 5MB, JPG/PNG/GIF/WEBP)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload avatar cho user hiện tại
    
    **Requirements:**
    - File type: JPG, JPEG, PNG, GIF, WEBP
    - Max size: 5MB
    - Auto resize: 400x400px (Cloudinary)
    - Auto optimize: Quality & format (Cloudinary)
    
    **Upload Process:**
    1. File được validate (type, size)
    2. Upload lên Cloudinary
    3. Auto resize về 400x400px
    4. Auto optimize quality
    5. Database cập nhật với Cloudinary URL
    6. Avatar cũ sẽ được xóa (nếu có)
    
    **Response:**
    - User object với `avatar_url` mới
    - `avatar_url` sẽ là Cloudinary URL format:
      `https://res.cloudinary.com/{cloud_name}/image/upload/...`
    
    **Example với Python requests:**
    ```python
    import requests
    
    url = "https://your-api.railway.app/api/v1/users/me/avatar"
    headers = {"Authorization": f"Bearer {access_token}"}
    files = {"file": open("avatar.jpg", "rb")}
    
    response = requests.put(url, headers=headers, files=files)
    user = response.json()
    print(user["avatar_url"])  # Cloudinary URL
    ```
    
    **Example với Swift:**
    ```swift
    let url = URL(string: "https://your-api.railway.app/api/v1/users/me/avatar")!
    var request = URLRequest(url: url)
    request.httpMethod = "PUT"
    request.setValue("Bearer \\(token)", forHTTPHeaderField: "Authorization")
    
    let boundary = UUID().uuidString
    request.setValue("multipart/form-data; boundary=\\(boundary)", 
                     forHTTPHeaderField: "Content-Type")
    
    var body = Data()
    body.append("--\\(boundary)\\r\\n")
    body.append("Content-Disposition: form-data; name=\\"file\\"; filename=\\"avatar.jpg\\"\\r\\n")
    body.append("Content-Type: image/jpeg\\r\\n\\r\\n")
    body.append(imageData)
    body.append("\\r\\n--\\(boundary)--\\r\\n")
    
    request.httpBody = body
    // ... URLSession.shared.dataTask ...
    ```
    """
    updated_user = await UserService.update_avatar_from_file(db, current_user.id, file)
    return updated_user


@router.put("/me/avatar/url", response_model=UserResponse)
async def update_avatar_url(
    avatar_update: UserAvatarUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cập nhật avatar từ URL (không upload file)
    
    **Use Cases:**
    - Avatar đã có sẵn trên Cloudinary
    - Avatar từ OAuth provider (Google, Apple)
    - Avatar từ CDN khác
    
    **Request Body:**
    ```json
    {
        "avatar_url": "https://res.cloudinary.com/xxx/image/upload/v1/avatar.jpg"
    }
    ```
    
    **Note:** URL nên là HTTPS để bảo mật
    """
    updated_user = UserService.update_avatar(db, current_user.id, avatar_update)
    return updated_user


@router.delete("/me/avatar", response_model=UserResponse)
async def delete_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Xóa avatar của user hiện tại
    
    **Actions:**
    - Set `avatar_url` = `null` trong database
    - Xóa file khỏi Cloudinary (optional, để tiết kiệm storage)
    
    **Response:**
    - User object với `avatar_url` = `null`
    """
    from app.schemas.user import UserUpdate
    
    user_update = UserUpdate(avatar_url=None)
    updated_user = UserService.update_user(db, current_user.id, user_update)
    
    # Optional: Delete from Cloudinary
    if current_user.avatar_url:
        try:
            from app.utils.cloudinary_upload import CloudinaryUploadService
            await CloudinaryUploadService.delete_avatar(current_user.avatar_url)
        except Exception as e:
            print(f"Warning: Could not delete avatar from Cloudinary: {e}")
    
    return updated_user


# ==================== OTHER ENDPOINTS ====================

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