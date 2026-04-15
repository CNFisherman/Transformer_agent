"""Chat 路由"""
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
from src.agent import get_rag_agent
from src.models import User
from src.auth import get_current_user

router = APIRouter()


class ChatRequest(BaseModel):
    """对话请求"""
    question: str = Field(..., description="用户问题", min_length=1)
    use_score: bool = Field(default=False, description="是否返回相似度分数")
    threshold: float = Field(default=1.5, description="相似度阈值")


class Source(BaseModel):
    """来源文档"""
    content: str
    source: str
    title: Optional[str] = None
    security_level: Optional[int] = None
    score: Optional[float] = None
    doc_id: Optional[int] = None  # 文档ID，用于下载


class ChatResponse(BaseModel):
    """对话响应"""
    answer: str
    sources: List[Source] = []
    user_context: Optional[dict] = None  # 用户上下文信息


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """问答接口（带权限控制）"""
    import traceback
    try:
        agent = get_rag_agent()

        # 构建用户权限上下文
        user_context = {
            "user_id": current_user.id,
            "username": current_user.username,
            "department": current_user.department,
            "security_level": current_user.get_security_level(),
            "accessible_departments": current_user.get_accessible_departments(),
            "roles": [r.name for r in current_user.roles]
        }

        if request.use_score:
            result = agent.query_with_score(
                request.question, 
                request.threshold,
                user_context=user_context
            )
        else:
            result = agent.query(
                request.question,
                user_context=user_context
            )

        return ChatResponse(
            answer=result["answer"],
            sources=[
                Source(
                    content=src.get("content", ""),
                    source=src.get("source", ""),
                    title=src.get("title"),
                    security_level=src.get("security_level"),
                    score=src.get("score"),
                    doc_id=src.get("doc_id")
                )
                for src in result["sources"]
            ],
            user_context=user_context
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[ERROR] Chat error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/chat/context")
async def get_chat_context(
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的聊天上下文"""
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "department": current_user.department,
        "security_level": current_user.get_security_level(),
        "security_level_name": {1: "公开", 2: "内部", 3: "机密", 4: "绝密"}.get(
            current_user.get_security_level(), "未知"
        ),
        "accessible_departments": current_user.get_accessible_departments(),
        "roles": [r.name for r in current_user.roles]
    }
