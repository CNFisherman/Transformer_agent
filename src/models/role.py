"""
角色和权限模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Table, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from src.models import Base


# 角色-权限关联表
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True)
)


class Role(Base):
    """角色模型"""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(255))
    security_level = Column(Integer, default=1)  # 安全等级: 1-公开, 2-内部, 3-机密, 4-绝密
    accessible_departments = Column(JSON, default=list)  # 可访问的部门列表，*表示全部
    is_system = Column(Boolean, default=False)  # 系统内置角色，不可删除
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    users = relationship("User", secondary="user_roles", back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")


class Permission(Base):
    """权限模型"""
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    code = Column(String(50), unique=True, index=True, nullable=False)  # 权限代码，如 doc:read, doc:write
    description = Column(String(255))
    category = Column(String(50))  # 权限分类：doc, user, system
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


# 预设权限
DEFAULT_PERMISSIONS = [
    # 文档权限
    {"name": "查看公开文档", "code": "doc:read:public", "category": "doc"},
    {"name": "查看内部文档", "code": "doc:read:internal", "category": "doc"},
    {"name": "查看机密文档", "code": "doc:read:confidential", "category": "doc"},
    {"name": "查看绝密文档", "code": "doc:read:topsecret", "category": "doc"},
    {"name": "上传文档", "code": "doc:write", "category": "doc"},
    {"name": "下载文档", "code": "doc:download", "category": "doc"},
    {"name": "删除文档", "code": "doc:delete", "category": "doc"},
    {"name": "管理文档元数据", "code": "doc:metadata", "category": "doc"},
    
    # 用户权限
    {"name": "查看用户", "code": "user:read", "category": "user"},
    {"name": "创建用户", "code": "user:create", "category": "user"},
    {"name": "编辑用户", "code": "user:update", "category": "user"},
    {"name": "删除用户", "code": "user:delete", "category": "user"},
    {"name": "分配角色", "code": "user:assign_role", "category": "user"},
    
    # 系统权限
    {"name": "系统管理", "code": "system:admin", "category": "system"},
    {"name": "查看日志", "code": "system:log", "category": "system"},
    {"name": "重建索引", "code": "system:reindex", "category": "system"},
]

# 预设角色
DEFAULT_ROLES = [
    {
        "name": "访客",
        "description": "访客角色，仅可查看公开文档",
        "security_level": 1,
        "accessible_departments": [],
        "permissions": ["doc:read:public"]
    },
    {
        "name": "普通员工",
        "description": "普通员工，可查看公开和内部文档",
        "security_level": 2,
        "accessible_departments": [],  # 仅可访问自己部门
        "permissions": ["doc:read:public", "doc:read:internal", "doc:download"]
    },
    {
        "name": "部门主管",
        "description": "部门主管，可查看公开、内部和机密文档",
        "security_level": 3,
        "accessible_departments": ["*"],  # 可访问所有部门
        "permissions": ["doc:read:public", "doc:read:internal", "doc:read:confidential", "doc:download", "doc:write"]
    },
    {
        "name": "高管",
        "description": "高管，可查看所有级别文档",
        "security_level": 4,
        "accessible_departments": ["*"],
        "permissions": ["doc:read:public", "doc:read:internal", "doc:read:confidential", "doc:read:topsecret", "doc:download", "doc:write", "doc:delete", "doc:metadata"]
    },
    {
        "name": "系统管理员",
        "description": "系统管理员，拥有全部权限",
        "security_level": 4,
        "accessible_departments": ["*"],
        "permissions": ["system:admin", "system:log", "system:reindex", "user:read", "user:create", "user:update", "user:delete", "user:assign_role"],
        "is_system": True
    },
]
