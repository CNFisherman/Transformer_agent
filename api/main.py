"""FastAPI 主入口"""
import os
from pathlib import Path
from typing import List
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import shutil

from api.routes import chat
from api.routes.auth_routes import router as auth_router
from api.routes.fault_routes import router as fault_router
from config.settings import settings
from src.models import init_db
from src.auth import init_default_data

app = FastAPI(
    title="Enterprise AI Agent",
    description="企业智能体 API - 文档问答系统",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(auth_router, prefix="/api/v1")
app.include_router(fault_router, prefix="/api/v1")

# 挂载静态文件
web_path = Path(__file__).parent.parent / "web"
app.mount("/web", StaticFiles(directory=str(web_path)), name="web")

@app.get("/")
async def root():
    """根路径重定向到登录页"""
    return RedirectResponse(url="/web/login.html")


# ============ 文件管理接口 ============

class FolderModel(BaseModel):
    """文件夹模型"""
    name: str
    path: str
    is_dir: bool
    children: List["FolderModel"] = []


@app.get("/api/v1/files")
async def list_files():
    """列出文档目录结构（树形）"""
    try:
        if not settings.DOCUMENTS_PATH.exists():
            return JSONResponse({"tree": []})
        
        def build_tree(path: Path, base_path: Path):
            """递归构建树形结构"""
            items = []
            try:
                for item in sorted(path.iterdir()):
                    try:
                        if item.is_file():
                            items.append({
                                "name": item.name,
                                "path": str(item.relative_to(base_path)),
                                "is_dir": False
                            })
                        elif item.is_dir():
                            children = build_tree(item, base_path)
                            items.append({
                                "name": item.name,
                                "path": str(item.relative_to(base_path)),
                                "is_dir": True,
                                "children": children
                            })
                    except Exception:
                        continue
            except Exception:
                pass
            return items
        
        tree = build_tree(settings.DOCUMENTS_PATH, settings.DOCUMENTS_PATH)
        return JSONResponse({"tree": tree})
    except Exception as e:
        return JSONResponse({"tree": [], "error": str(e)}, status_code=500)


@app.post("/api/v1/files/upload")
async def upload_file(
    folder: str = "",
    file: UploadFile = File(...)
):
    """上传文件到指定文件夹"""
    try:
        # 确定目标目录
        if folder and folder != ".":
            target_dir = settings.DOCUMENTS_PATH / folder
        else:
            target_dir = settings.DOCUMENTS_PATH
        
        # 创建目录
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存文件
        file_path = target_dir / file.filename
        
        # 如果文件已存在，添加时间戳
        if file_path.exists():
            import time
            name = file_path.stem
            ext = file_path.suffix
            file_path = target_dir / f"{name}_{int(time.time())}{ext}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return JSONResponse({
            "success": True,
            "message": f"文件 {file.filename} 上传成功",
            "path": str(file_path.relative_to(settings.DOCUMENTS_PATH))
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/files/create-folder")
async def create_folder(name: str, parent: str = ""):
    """创建文件夹"""
    try:
        if parent and parent != ".":
            target_dir = settings.DOCUMENTS_PATH / parent / name
        else:
            target_dir = settings.DOCUMENTS_PATH / name
        
        if target_dir.exists():
            raise HTTPException(status_code=400, detail="文件夹已存在")
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        return JSONResponse({
            "success": True,
            "message": f"文件夹 {name} 创建成功",
            "path": str(target_dir.relative_to(settings.DOCUMENTS_PATH))
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/files")
async def delete_file(path: str):
    """删除文件或文件夹"""
    try:
        target_path = settings.DOCUMENTS_PATH / path
        
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="文件或文件夹不存在")
        
        if target_path.is_file():
            target_path.unlink()
            message = f"文件 {path} 删除成功"
        else:
            shutil.rmtree(target_path)
            message = f"文件夹 {path} 删除成功"
        
        return JSONResponse({"success": True, "message": message})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ingest")
async def trigger_ingest():
    """触发文档重建索引"""
    from scripts.ingest import load_documents
    from src.vectorstore import VectorStoreManager
    
    try:
        documents = load_documents()
        
        if not documents:
            return JSONResponse({
                "success": False,
                "message": "未找到任何文档"
            })
        
        vectorstore_manager = VectorStoreManager()
        vectorstore_manager.create_vectorstore(documents)
        vectorstore_manager.save()
        
        return JSONResponse({
            "success": True,
            "message": f"索引重建成功，共处理 {len(documents)} 个文档"
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ 健康检查 ============

@app.get("/")
async def root():
    return {
        "name": "Enterprise AI Agent",
        "version": "2.0.0",
        "status": "running",
        "auth": "enabled"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    # 确保data目录存在
    os.makedirs("data", exist_ok=True)
    os.makedirs("documents", exist_ok=True)
    
    # 初始化数据库表
    init_db()
    
    # 初始化默认数据
    from src.models import SessionLocal
    db = SessionLocal()
    try:
        init_default_data(db)
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
