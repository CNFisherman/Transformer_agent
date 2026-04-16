"""故障处理路由"""
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
from src.models import User
from src.auth import get_current_user
import os
from pathlib import Path

router = APIRouter(prefix="/fault", tags=["故障处理"])

# 故障处理文档路径（多个目录）
FAULT_DOCS_PATHS = [
    Path(__file__).parent.parent.parent / "raw" / "故障处理",
    Path(__file__).parent.parent.parent / "documents" / "raw" / "故障处理",
]


class FaultRequest(BaseModel):
    """故障请求"""
    fault_desc: str = Field(..., description="故障描述", min_length=1)


class FaultSource(BaseModel):
    """参考来源"""
    content: str
    source: str
    title: Optional[str] = None


class FaultResponse(BaseModel):
    """故障处理响应"""
    answer: str
    sources: List[FaultSource] = []


@router.post("/diagnose", response_model=FaultResponse)
async def diagnose_fault(
    request: FaultRequest,
    current_user: User = Depends(get_current_user)
):
    """故障诊断接口"""
    try:
        from config.prompts import FAULT_SYSTEM_PROMPT, FAULT_USER_PROMPT
        from src.llm import chat_manager
        
        # 加载故障处理文档
        context_parts = []
        sources = []
        
        def read_file(path):
            """读取文本文件"""
            for encoding in ['utf-8', 'gbk', 'gb2312']:
                try:
                    with open(path, 'r', encoding=encoding) as f:
                        return f.read()
                except:
                    continue
            return ""
        
        def read_excel(path):
            """读取 Excel 文件"""
            from src.loaders.excel_loader import read_excel as _read_excel
            return _read_excel(path)
        
        # 遍历所有故障文档目录
        for FAULT_DOCS_PATH in FAULT_DOCS_PATHS:
            if FAULT_DOCS_PATH.exists():
                # 读取 Markdown 文件
                for doc_path in FAULT_DOCS_PATH.rglob("*.md"):
                    content = read_file(doc_path)
                    if content:
                        relative_path = doc_path.relative_to(FAULT_DOCS_PATH.parent.parent)
                        context_parts.append(f"【{relative_path}】\n{content[:2000]}")
                        sources.append({
                            "content": content[:500],
                            "source": str(relative_path),
                            "title": doc_path.stem
                        })
                # 读取文本文件
                for doc_path in FAULT_DOCS_PATH.rglob("*.txt"):
                    content = read_file(doc_path)
                    if content:
                        relative_path = doc_path.relative_to(FAULT_DOCS_PATH.parent.parent)
                        context_parts.append(f"【{relative_path}】\n{content[:2000]}")
                        sources.append({
                            "content": content[:500],
                            "source": str(relative_path),
                            "title": doc_path.stem
                        })
                # 读取 Excel 文件
                for doc_path in FAULT_DOCS_PATH.rglob("*.xlsx"):
                    content = read_excel(doc_path)
                    if content:
                        relative_path = doc_path.relative_to(FAULT_DOCS_PATH.parent.parent)
                        context_parts.append(f"【{relative_path}】\n{content[:3000]}")
                        sources.append({
                            "content": content[:500],
                            "source": str(relative_path),
                            "title": doc_path.stem
                        })
        
        if not context_parts:
            return FaultResponse(
                answer="暂无故障处理文档，请联系管理员上传相关文档。",
                sources=[]
            )
        
        context = "\n\n".join(context_parts)
        
        # 构建 prompt
        user_prompt = FAULT_USER_PROMPT.format(
            context=context,
            question=request.fault_desc
        )
        
        # 调用 LLM
        from langchain_core.messages import HumanMessage, SystemMessage
        messages = [
            SystemMessage(content=FAULT_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]
        response = chat_manager.llm.invoke(messages)
        answer = response.content
        
        if hasattr(answer, 'content'):
            answer = answer.content
        
        return FaultResponse(
            answer=answer,
            sources=[FaultSource(**s) for s in sources]
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"故障诊断失败: {str(e)}")


@router.get("/workshops")
async def list_workshops(
    current_user: User = Depends(get_current_user)
):
    """获取车间列表"""
    workshops = []
    
    if FAULT_DOCS_PATH.exists():
        for item in FAULT_DOCS_PATH.iterdir():
            if item.is_dir() and item.name != "README.md":
                workshops.append({
                    "name": item.name,
                    "path": str(item.relative_to(FAULT_DOCS_PATH.parent.parent))
                })
    
    return {"workshops": workshops}


@router.get("/documents")
async def list_fault_docs(
    workshop: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """获取故障处理文档列表"""
    docs = []
    
    if workshop:
        search_path = FAULT_DOCS_PATH / workshop
    else:
        search_path = FAULT_DOCS_PATH
    
    if search_path.exists():
        for doc_path in search_path.rglob("*.md"):
            relative = doc_path.relative_to(FAULT_DOCS_PATH.parent.parent)
            docs.append({
                "name": doc_path.name,
                "path": str(relative),
                "type": "markdown"
            })
        for doc_path in search_path.rglob("*.txt"):
            relative = doc_path.relative_to(FAULT_DOCS_PATH.parent.parent)
            docs.append({
                "name": doc_path.name,
                "path": str(relative),
                "type": "text"
            })
        for doc_path in search_path.rglob("*.xlsx"):
            relative = doc_path.relative_to(FAULT_DOCS_PATH.parent.parent)
            docs.append({
                "name": doc_path.name,
                "path": str(relative),
                "type": "excel"
            })
    
    return {"documents": docs}
