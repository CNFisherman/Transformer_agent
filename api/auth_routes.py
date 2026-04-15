"""
认证路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from pydantic import BaseModel, EmailStr

from src.models import get_db, User
from src.auth import (
    verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user, get_password_hash
)
from src.auth.role import Role

router = APIRouter(prefix="/auth", tags=["认证"])


class Token(BaseModel):
    access_token: str
    token_type: str


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str = None
    department: str = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str = None
    department: str = None
    is_active: bool
    is_superuser: bool
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录"""
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """注册新用户（需要管理员权限）"""
    if not current_user.has_permission("user:create") and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有创建用户的权限"
        )
    
    # 检查用户名是否存在
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否存在
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被使用"
        )
    
    # 创建用户
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        department=user_data.department,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """获取当前用户信息"""
    return current_user


@router.get("/me/permissions")
async def get_user_permissions(
    current_user: User = Depends(get_current_user)
):
    """获取当前用户权限"""
    permissions = []
    for role in current_user.roles:
        for perm in role.permissions:
            if perm.code not in [p["code"] for p in permissions]:
                permissions.append({
                    "code": perm.code,
                    "name": perm.name,
                    "category": perm.category
                })
    
    return {
        "username": current_user.username,
        "security_level": current_user.get_security_level(),
        "accessible_departments": current_user.get_accessible_departments(),
        "roles": [role.name for role in current_user.roles],
        "permissions": permissions
    }


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """用户登出（前端删除token即可）"""
    return {"message": "已登出"}
