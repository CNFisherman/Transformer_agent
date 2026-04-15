"""
文档管理路由（含权限控制）
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import os
import shutil
from datetime import datetime

from src.models import get_db, User, Document, DocumentAccessLog
from src.auth import get_current_user, require_permission
from src.models.document import SECURITY_LEVELS, DOCUMENT_CATEGORIES

router = APIRouter(prefix="/documents", tags=["文档管理"])


class DocumentMetadata(BaseModel):
    file_path: str
    title: Optional[str] = None
    category: Optional[str] = None
    department: Optional[str] = None
    tags: Optional[str] = None
    summary: Optional[str] = None
    security_level: Optional[int] = 1
    is_classified: Optional[bool] = False
    accessible_departments: Optional[str] = None  # 逗号分隔


class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    file_type: str
    file_size: int
    title: str
    category: str
    department: str
    tags: str
    summary: str
    security_level: int
    security_level_name: str
    is_classified: bool
    accessible_departments: str


def log_access(db: Session, document_id: int, user_id: int, action: str, ip_address: str = None):
    """记录文档访问日志"""
    log = DocumentAccessLog(
        document_id=document_id,
        user_id=user_id,
        action=action,
        ip_address=ip_address
    )
    db.add(log)
    db.commit()


@router.get("/", response_model=List[dict])
async def list_documents(
    category: Optional[str] = None,
    department: Optional[str] = None,
    security_level: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取文档列表（根据权限过滤）"""
    query = db.query(Document).filter(Document.is_active == True)
    
    # 按条件过滤
    if category:
        query = query.filter(Document.category == category)
    if department:
        query = query.filter(Document.department == department)
    if security_level:
        query = query.filter(Document.security_level <= security_level)
    
    documents = query.all()
    
    # 过滤用户无权限访问的文档
    accessible_docs = []
    for doc in documents:
        if doc.can_access(current_user):
            accessible_docs.append({
                "id": doc.id,
                "filename": doc.filename,
                "file_path": doc.file_path,
                "file_type": doc.file_type,
                "title": doc.title,
                "category": doc.category,
                "department": doc.department,
                "security_level": doc.security_level,
                "security_level_name": doc.get_security_level_name(),
                "is_classified": doc.is_classified,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
            })
    
    return accessible_docs


@router.get("/categories")
async def get_categories():
    """获取文档分类列表"""
    return DOCUMENT_CATEGORIES


@router.get("/security-levels")
async def get_security_levels():
    """获取安全等级列表"""
    return [{"level": k, "name": v} for k, v in SECURITY_LEVELS.items()]


@router.get("/{doc_id}", response_model=dict)
async def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取文档详情"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if not doc.can_access(current_user):
        raise HTTPException(status_code=403, detail="没有权限访问此文档")
    
    # 记录访问日志
    log_access(db, doc_id, current_user.id, "view")
    
    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_path": doc.file_path,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "title": doc.title,
        "category": doc.category,
        "department": doc.department,
        "tags": doc.tags,
        "summary": doc.summary,
        "security_level": doc.security_level,
        "security_level_name": doc.get_security_level_name(),
        "is_classified": doc.is_classified,
        "accessible_departments": doc.accessible_departments,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
    }


@router.put("/{doc_id}/metadata", response_model=dict)
async def update_document_metadata(
    doc_id: int,
    metadata: DocumentMetadata,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("doc:metadata"))
):
    """更新文档元数据"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if metadata.title is not None:
        doc.title = metadata.title
    if metadata.category is not None:
        doc.category = metadata.category
    if metadata.department is not None:
        doc.department = metadata.department
    if metadata.tags is not None:
        doc.tags = metadata.tags
    if metadata.summary is not None:
        doc.summary = metadata.summary
    if metadata.security_level is not None:
        doc.security_level = metadata.security_level
        doc.is_classified = metadata.security_level > 1
    if metadata.accessible_departments is not None:
        doc.accessible_departments = metadata.accessible_departments
    
    doc.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "文档元数据已更新"}


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("doc:delete"))
):
    """删除文档"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 删除物理文件
    file_path = Path("documents") / doc.file_path
    if file_path.exists():
        file_path.unlink()
    
    # 删除数据库记录
    db.delete(doc)
    db.commit()
    
    return {"message": "文档已删除"}


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("doc:write"))
):
    """上传文档"""
    # 保存文件
    upload_dir = Path("documents") / folder if folder else Path("documents")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 获取文件大小
    file_size = file_path.stat().st_size
    
    # 获取文件类型
    file_ext = file_path.suffix.lower().lstrip(".")
    
    # 创建文档记录
    doc = Document(
        filename=file.filename,
        file_path=str(file_path.relative_to("documents")),
        file_type=file_ext,
        file_size=file_size,
        category="其他",
        department=current_user.department or "未分类",
        security_level=1
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    return {
        "message": "文件上传成功",
        "document_id": doc.id,
        "filename": doc.filename
    }


@router.get("/download/{doc_id}")
async def download_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("doc:download"))
):
    """下载文档"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if not doc.can_access(current_user):
        raise HTTPException(status_code=403, detail="没有权限下载此文档")
    
    # 记录下载日志
    log_access(db, doc_id, current_user.id, "download")
    
    file_path = Path("documents") / doc.file_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(
        path=str(file_path),
        filename=doc.filename,
        media_type="application/octet-stream"
    )


@router.get("/logs/")
async def get_access_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system:log"))
):
    """获取访问日志"""
    logs = db.query(DocumentAccessLog).order_by(
        DocumentAccessLog.accessed_at.desc()
    ).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "document_id": log.document_id,
            "document_name": log.document.filename if log.document else "已删除",
            "username": log.user.username if log.user else "已删除",
            "action": log.action,
            "ip_address": log.ip_address,
            "accessed_at": log.accessed_at.isoformat()
        }
        for log in logs
    ]
