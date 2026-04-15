"""
用户模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from src.models import Base


# 用户-角色关联表
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True)
)


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    department = Column(String(100))  # 所属部门
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)  # 超级管理员
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

    # 关系
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    document_access_logs = relationship("DocumentAccessLog", back_populates="user")

    def has_role(self, role_name: str) -> bool:
        """检查用户是否拥有指定角色"""
        return any(role.name == role_name for role in self.roles)

    def has_permission(self, permission_name: str) -> bool:
        """检查用户是否拥有指定权限"""
        if self.is_superuser:
            return True
        for role in self.roles:
            for permission in role.permissions:
                if permission.name == permission_name:
                    return True
        return False

    def get_security_level(self) -> int:
        """获取用户的安全等级（1-4），用于涉密文档访问控制"""
        # 超级管理员拥有最高权限
        if self.is_superuser:
            return 4
        # 根据角色计算安全等级
        max_level = 0
        for role in self.roles:
            if role.security_level > max_level:
                max_level = role.security_level
        return max_level if max_level > 0 else 1

    def get_accessible_departments(self) -> list:
        """获取用户可访问的部门列表"""
        if self.is_superuser:
            return ["*"]  # 可访问所有部门
        departments = set()
        for role in self.roles:
            if role.accessible_departments:
                departments.update(role.accessible_departments)
        return list(departments) if departments else []
