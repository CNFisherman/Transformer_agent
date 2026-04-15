"""
用户管理路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from src.models import get_db, User
from src.auth import get_current_user, require_permission, require_role, get_password_hash
from src.auth.role import Role

router = APIRouter(prefix="/users", tags=["用户管理"])


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None


class RoleAssign(BaseModel):
    user_id: int
    role_ids: List[int]


@router.get("/", response_model=List[dict])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:read"))
):
    """获取用户列表"""
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "department": u.department,
            "is_active": u.is_active,
            "is_superuser": u.is_superuser,
            "roles": [r.name for r in u.roles],
            "security_level": u.get_security_level(),
            "last_login": u.last_login.isoformat() if u.last_login else None
        }
        for u in users
    ]


@router.get("/{user_id}", response_model=dict)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:read"))
):
    """获取用户详情"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "department": user.department,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "roles": [{"id": r.id, "name": r.name, "description": r.description} for r in user.roles],
        "security_level": user.get_security_level(),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None
    }


@router.put("/{user_id}", response_model=dict)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:update"))
):
    """更新用户信息"""
    # 普通用户只能修改自己
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="只能修改自己的信息")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 只能管理员修改其他用户
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="没有权限修改此用户")
    
    if user_data.email:
        user.email = user_data.email
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.department is not None:
        user.department = user_data.department
    if user_data.is_active is not None and current_user.is_superuser:
        user.is_active = user_data.is_active
    
    db.commit()
    
    return {"message": "用户信息已更新"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:delete"))
):
    """删除用户"""
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if user.is_superuser:
        raise HTTPException(status_code=403, detail="不能删除超级管理员")
    
    db.delete(user)
    db.commit()
    
    return {"message": "用户已删除"}


@router.post("/roles/assign")
async def assign_roles(
    role_data: RoleAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:assign_role"))
):
    """分配用户角色"""
    user = db.query(User).filter(User.id == role_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if user.is_superuser:
        raise HTTPException(status_code=403, detail="不能修改超级管理员的角色")
    
    roles = db.query(Role).filter(Role.id.in_(role_data.role_ids)).all()
    user.roles = roles
    db.commit()
    
    return {"message": "角色分配成功"}


@router.get("/roles/list", response_model=List[dict])
async def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:read"))
):
    """获取角色列表"""
    roles = db.query(Role).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "security_level": r.security_level,
            "is_system": r.is_system,
            "permissions": [p.code for p in r.permissions]
        }
        for r in roles
    ]
