"""认证路由"""
from datetime import timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.models import get_db, User
from src.auth import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/auth", tags=["认证"])


class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    department: str
    roles: List[str]
    security_level: int

    class Config:
        from_attributes = True


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """用户登录"""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "roles": [r.name for r in user.roles],
            "security_level": user.get_security_level(),
            "department": user.department,
            "is_superuser": user.is_superuser
        },
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(db: Session = Depends(get_db), token: str = Depends(__import__('src.auth', fromlist=['oauth2_scheme']).oauth2_scheme)):
    """获取当前用户信息"""
    from src.auth import decode_token
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="无效的认证信息")
    
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        department=user.department,
        roles=[r.name for r in user.roles],
        security_level=user.get_security_level()
    )


@router.post("/register")
async def register(
    username: str,
    password: str,
    email: str,
    department: str,
    db: Session = Depends(get_db)
):
    """注册新用户"""
    from src.auth import get_password_hash
    from src.models.role import Role
    
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 查找默认角色
    default_role = db.query(Role).filter(Role.name == "普通员工").first()
    if not default_role:
        raise HTTPException(status_code=500, detail="默认角色不存在")
    
    new_user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        department=department,
        is_active=True
    )
    new_user.roles.append(default_role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "注册成功", "user_id": new_user.id}
