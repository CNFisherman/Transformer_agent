"""
认证和安全工具
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from src.models import get_db, User
from src.models.role import Role, Permission, DEFAULT_PERMISSIONS, DEFAULT_ROLES
import os

# JWT配置
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT Token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """解码JWT Token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """获取当前登录用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证失败，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    db.commit()
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")
    return current_user


def require_permission(permission_code: str):
    """权限验证装饰器工厂"""
    async def permission_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if not current_user.has_permission(permission_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"没有权限: {permission_code}"
            )
        return current_user
    return permission_checker


def require_role(role_name: str):
    """角色验证装饰器工厂"""
    async def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if not current_user.has_role(role_name) and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要角色: {role_name}"
            )
        return current_user
    return role_checker


def init_default_data(db: Session):
    """初始化默认数据"""
    # 检查是否已初始化
    existing_roles = db.query(Role).first()
    if existing_roles:
        return
    
    # 创建默认权限
    permission_map = {}
    for perm_data in DEFAULT_PERMISSIONS:
        permission = Permission(**perm_data)
        db.add(permission)
        permission_map[perm_data["code"]] = permission
    
    # 创建默认角色
    role_map = {}
    for role_data in DEFAULT_ROLES:
        permissions = role_data.pop("permissions", [])
        role = Role(**role_data)
        db.add(role)
        role_map[role_data["name"]] = role
        
        # 关联权限
        for perm_code in permissions:
            if perm_code in permission_map:
                role.permissions.append(permission_map[perm_code])
    
    # 创建默认管理员账户
    admin_user = User(
        username="admin",
        email="admin@company.com",
        hashed_password=get_password_hash("admin123"),  # 生产环境请修改！
        full_name="系统管理员",
        department="信息中心",
        is_superuser=True,
        is_active=True
    )
    admin_user.roles.append(role_map["系统管理员"])
    db.add(admin_user)
    
    # 创建测试账户
    test_user = User(
        username="test",
        email="test@company.com",
        hashed_password=get_password_hash("test123"),
        full_name="测试用户",
        department="干变车间",
        is_active=True
    )
    test_user.roles.append(role_map["普通员工"])
    db.add(test_user)
    
    db.commit()
    print("[OK] 默认角色、权限和用户已创建")
    print("[OK] 管理员账户: admin / admin123")
    print("[OK] 测试账户: test / test123")
