"""
文档模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from src.models import Base


# 安全等级常量
SECURITY_LEVELS = {
    1: "公开",
    2: "内部",
    3: "机密",
    4: "绝密"
}

# 文档分类
DOCUMENT_CATEGORIES = [
    "设备清单",      # 设备相关
    "可行性报告",     # 项目可行性
    "接口文档",      # 技术文档
    "财务报表",      # 财务相关
    "人事文档",      # 人事相关
    "设计图纸",      # 设计相关
    "生产计划",      # 生产相关
    "质量报告",      # 质量相关
    "合同协议",      # 法务相关
    "行政公文",      # 行政相关
    "培训资料",      # 培训相关
    "其他"          # 其他
]


class Document(Base):
    """文档模型"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)  # 文件名
    file_path = Column(String(500), unique=True, index=True, nullable=False)  # 文件路径（相对）
    file_type = Column(String(20))  # 文件类型：pdf, docx, doc, txt等
    file_size = Column(Integer)  # 文件大小（字节）
    
    # 元数据
    title = Column(String(255))  # 文档标题
    category = Column(String(50))  # 文档分类
    department = Column(String(100))  # 所属部门
    tags = Column(String(500))  # 标签，逗号分隔
    summary = Column(Text)  # 文档摘要
    
    # 安全相关
    security_level = Column(Integer, default=1)  # 涉密等级：1-公开, 2-内部, 3-机密, 4-绝密
    is_classified = Column(Boolean, default=False)  # 是否涉密
    accessible_departments = Column(String(500))  # 可访问部门，逗号分隔，为空表示不限
    
    # 状态
    is_active = Column(Boolean, default=True)  # 是否启用
    indexed_at = Column(DateTime)  # 索引时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    access_logs = relationship("DocumentAccessLog", back_populates="document")

    def can_access(self, user) -> bool:
        """检查用户是否有权访问此文档"""
        # 超级管理员可访问所有
        if user.is_superuser:
            return True
        
        # 检查安全等级
        user_level = user.get_security_level()
        if self.security_level > user_level:
            return False
        
        # 检查部门访问权限
        accessible_depts = self.accessible_departments
        if accessible_depts:  # 如果设置了部门限制
            user_depts = user.get_accessible_departments()
            if "*" not in user_depts:  # 非全权限
                # 检查是否有交集
                dept_list = [d.strip() for d in accessible_depts.split(",")]
                has_access = any(d in user_depts or d == user.department for d in dept_list)
                if not has_access:
                    return False
        
        return True

    def get_security_level_name(self) -> str:
        """获取安全等级名称"""
        return SECURITY_LEVELS.get(self.security_level, "未知")


class DocumentAccessLog(Base):
    """文档访问日志"""
    __tablename__ = "document_access_logs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(50))  # action: view, download, search
    ip_address = Column(String(50))
    user_agent = Column(String(255))
    accessed_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    document = relationship("Document", back_populates="access_logs")
    user = relationship("User", back_populates="document_access_logs")
