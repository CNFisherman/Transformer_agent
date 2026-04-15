"""检索器"""
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from config.settings import settings
from src.vectorstore import VectorStoreManager


class Retriever:
    """检索器（支持权限过滤）"""

    def __init__(self, vectorstore_manager: VectorStoreManager):
        self.vectorstore_manager = vectorstore_manager
        self._retriever = None

    def _filter_by_permission(self, docs: List[Document], user_context: dict = None) -> List[Document]:
        """根据用户权限过滤文档"""
        if user_context is None:
            return docs
        
        user_security_level = user_context.get("security_level", 1)
        user_departments = user_context.get("accessible_departments", [])
        username = user_context.get("username", "anonymous")
        
        filtered_docs = []
        for doc in docs:
            # 获取文档安全等级（默认为1-公开）
            doc_security_level = doc.metadata.get("security_level", 1)
            
            # 检查安全等级
            if doc_security_level > user_security_level:
                print(f"[PERMISSION] 过滤文档 {doc.metadata.get('source', 'unknown')}: 安全等级 {doc_security_level} > 用户等级 {user_security_level}")
                continue
            
            # 检查部门权限
            accessible_depts = doc.metadata.get("accessible_departments", "")
            if accessible_depts:
                dept_list = [d.strip() for d in accessible_depts.split(",") if d.strip()]
                if dept_list:
                    # 如果设置了部门限制
                    if "*" not in user_departments:
                        user_dept = user_context.get("department", "")
                        if user_dept not in dept_list and not any(d in user_departments for d in dept_list):
                            print(f"[PERMISSION] 过滤文档 {doc.metadata.get('source', 'unknown')}: 部门权限限制")
                            continue
            
            filtered_docs.append(doc)
        
        return filtered_docs

    def get_retriever(self, top_k: int = None) -> RunnableLambda:
        """获取检索器"""
        if self.vectorstore_manager.vectorstore is None:
            raise ValueError("向量存储未初始化")

        k = top_k or settings.TOP_K

        self._retriever = self.vectorstore_manager.vectorstore.as_retriever(
            search_kwargs={"k": k}
        )

        return self._retriever

    def search(self, query: str, top_k: int = None, user_context: dict = None) -> List[Document]:
        """搜索相似文档（支持权限过滤）"""
        if self.vectorstore_manager.vectorstore is None:
            raise ValueError("向量存储未初始化")

        k = top_k or settings.TOP_K

        # 检索更多文档，因为会被过滤
        search_k = k * 3 if user_context else k
        
        docs = self.vectorstore_manager.vectorstore.similarity_search(
            query,
            k=search_k
        )
        
        # 根据权限过滤
        if user_context:
            docs = self._filter_by_permission(docs, user_context)
        
        # 返回最多 k 个文档
        return docs[:k]

    def search_with_score(
        self, 
        query: str, 
        top_k: int = None, 
        threshold: float = 0.7,
        user_context: dict = None
    ) -> List[Dict[str, Any]]:
        """带相似度分数的搜索（支持权限过滤）"""
        if self.vectorstore_manager.vectorstore is None:
            raise ValueError("向量存储未初始化")

        k = top_k or settings.TOP_K
        
        # 检索更多文档，因为会被过滤
        search_k = k * 3 if user_context else k

        results = self.vectorstore_manager.vectorstore.similarity_search_with_score(
            query,
            k=search_k
        )

        filtered_results = []
        for doc, score in results:
            if score <= threshold:  # 距离越小越相似
                # 检查权限
                if user_context:
                    user_security_level = user_context.get("security_level", 1)
                    doc_security_level = doc.metadata.get("security_level", 1)
                    
                    if doc_security_level > user_security_level:
                        continue
                    
                    accessible_depts = doc.metadata.get("accessible_departments", "")
                    if accessible_depts:
                        dept_list = [d.strip() for d in accessible_depts.split(",") if d.strip()]
                        if dept_list:
                            user_departments = user_context.get("accessible_departments", [])
                            if "*" not in user_departments:
                                user_dept = user_context.get("department", "")
                                if user_dept not in dept_list and not any(d in user_departments for d in dept_list):
                                    continue
                
                filtered_results.append({
                    "document": doc,
                    "score": score,
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", "unknown"),
                    "title": doc.metadata.get("title", "unknown"),
                    "security_level": doc.metadata.get("security_level", 1),
                    "doc_id": doc.metadata.get("doc_id")
                })
        
        # 返回最多 k 个结果
        return filtered_results[:k]
