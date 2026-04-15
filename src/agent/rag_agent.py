"""RAG Agent - 检索增强生成智能体"""
import re
from typing import List, Dict, Any, Optional
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from config.settings import settings
from config.prompts import RAG_SYSTEM_PROMPT, RAG_USER_PROMPT
from src.vectorstore import VectorStoreManager
from src.retriever import Retriever
from src.llm import chat_manager
from src.tools.file_tools import list_word_files, list_files_tool


# 不需要检索文档的关键词
GREETING_KEYWORDS = [
    "谢谢", "感谢", "谢了", "thx", "thanks", "thank you",
    "你好", "您好", "hi", "hello", "嗨", "嗨你好",
    "再见", "拜拜", " bye", "goodbye",
    "辛苦了", "赞", "好", "不错",
    "你是谁", "叫什么", "介绍下自己"
]


class RAGAgent:
    """RAG 问答智能体"""

    def __init__(self):
        self.vectorstore_manager = VectorStoreManager()
        self.retriever = Retriever(self.vectorstore_manager)
        self.chat_manager = chat_manager

    def initialize(self):
        """初始化 - 加载或创建向量存储"""
        if self.vectorstore_manager.exists():
            print("加载已有向量存储...")
            self.vectorstore_manager.load()
        else:
            print("向量存储不存在，请先运行 ingestion 脚本")
            raise FileNotFoundError("向量存储不存在，请先加载文档")

        # 初始化检索器
        self.retriever.get_retriever()

        print("RAG Agent 初始化完成 [OK]")

    def _format_docs(self, docs: List) -> str:
        """格式化文档为字符串"""
        return "\n\n---\n\n".join([doc.page_content for doc in docs])

    def _is_greeting(self, question: str) -> bool:
        """判断是否为寒暄类问题"""
        question_lower = question.lower().strip()
        # 检查是否包含寒暄关键词
        for keyword in GREETING_KEYWORDS:
            if keyword.lower() in question_lower:
                return True
        # 如果问题很短（少于5个字），也认为是寒暄
        if len(question.strip()) < 5:
            return True
        return False

    def _is_file_query(self, question: str) -> bool:
        """判断是否为文件列表查询"""
        question_lower = question.lower()
        file_keywords = ["列出", "列表", "罗列", "有哪些", "文件列表", "有什么文件", "文件夹"]
        word_keywords = ["word", "文档", "docx", ".doc"]
        
        has_file_keyword = any(k in question_lower for k in file_keywords)
        has_word_keyword = any(k in question_lower for k in word_keywords)
        
        # 如果问的是word相关，或者问的是文件列表
        if "word" in question_lower or "文档" in question_lower:
            return True
        if has_file_keyword and has_word_keyword:
            return True
        # 单独问word文件
        if "word文件" in question_lower or "docx" in question_lower or ".doc" in question_lower:
            return True
        return False
        return False

    def _is_deepseek_model(self) -> bool:
        """判断是否使用 DeepSeek 系列模型"""
        model_name = settings.OPENAI_MODEL.lower()
        return "deepseek" in model_name or "r1" in model_name

    def _process_thinking(self, text: str) -> str:
        """处理思考标签"""
        if not self._is_deepseek_model():
            # 非 DeepSeek 模型，移除 thinking 标签（前端显示三个点）
            text = re.sub(r'<think>[\s\S]*?</think>', '', text)
            return text

        # DeepSeek 模型，保留并格式化 thinking 标签
        def format_thinking(match):
            thinking = match.group(1).strip()
            return f'\n\n<thinking>\n{thinking}\n</thinking>\n\n'
        
        text = re.sub(r'<think>\s*([\s\S]*?)\s*</think>', format_thinking, text)
        return text

    def _direct_chat(self, question: str) -> str:
        """直接对话（不检索文档）"""
        return self.chat_manager.chat(
            question,
            system_prompt="你是一个友好、专业的企业智能助手。请用简短、自然的方式回答。"
        )

    def query(self, question: str, user_context: dict = None) -> Dict[str, Any]:
        """问答（支持用户权限上下文）"""
        # 0. 判断是否为寒暄
        if self._is_greeting(question):
            answer = self._direct_chat(question)
            return {
                "answer": answer,
                "sources": []
            }

        # 0.1 判断是否为文件列表查询
        if self._is_file_query(question):
            question_lower = question.lower()
            # 检查是否问的是 word 文件
            if "word" in question_lower or "docx" in question_lower or ".doc" in question_lower:
                answer = list_word_files.invoke({})
            else:
                # 其他文件列表
                answer = list_files_tool.invoke({})
            return {
                "answer": answer,
                "sources": []
            }

        # 1. 检索相关文档（带权限过滤）
        docs = self.retriever.search(question, user_context=user_context)
        context = self._format_docs(docs)

        # 2. 构建 Prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", RAG_SYSTEM_PROMPT),
            ("human", RAG_USER_PROMPT)
        ])

        # 3. 创建 RAG Chain
        rag_chain = (
            {"context": RunnablePassthrough(), "question": RunnablePassthrough()}
            | prompt
            | self.chat_manager.llm
            | StrOutputParser()
        )

        # 4. 生成回答
        answer = rag_chain.invoke({"context": context, "question": question})

        # 5. 处理思考标签
        answer = self._process_thinking(answer)

        return {
            "answer": answer,
            "sources": [
                {
                    "content": doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
                    "source": doc.metadata.get("source", "unknown"),
                    "title": doc.metadata.get("title", "unknown"),
                    "security_level": doc.metadata.get("security_level", 1),
                    "doc_id": doc.metadata.get("doc_id")
                }
                for doc in docs
            ]
        }

    def query_with_score(self, question: str, threshold: float = 1.5, user_context: dict = None) -> Dict[str, Any]:
        """带相似度分数的问答（支持用户权限上下文）"""
        # 0. 判断是否为寒暄
        if self._is_greeting(question):
            answer = self._direct_chat(question)
            return {
                "answer": answer,
                "sources": []
            }

        # 1. 检索相关文档（带分数和权限过滤）
        results = self.retriever.search_with_score(question, threshold=threshold, user_context=user_context)

        if not results:
            return {
                "answer": "我在知识库中没有找到与您问题相关的文档。",
                "sources": []
            }

        # 2. 构建上下文
        docs = [r["document"] for r in results]
        context = self._format_docs(docs)

        # 3. 构建 Prompt 并生成回答
        prompt = ChatPromptTemplate.from_messages([
            ("system", RAG_SYSTEM_PROMPT),
            ("human", RAG_USER_PROMPT)
        ])

        rag_chain = (
            {"context": RunnablePassthrough(), "question": RunnablePassthrough()}
            | prompt
            | self.chat_manager.llm
            | StrOutputParser()
        )

        answer = rag_chain.invoke({"context": context, "question": question})

        # 4. 处理思考标签
        answer = self._process_thinking(answer)

        return {
            "answer": answer,
            "sources": [
                {
                    "score": r["score"],
                    "content": r["content"][:300] + "..." if len(r["content"]) > 300 else r["content"],
                    "source": r["source"],
                    "title": r.get("title", "unknown"),
                    "security_level": r.get("security_level", 1),
                    "doc_id": r.get("doc_id")
                }
                for r in results
            ]
        }


# 全局实例
rag_agent: Optional[RAGAgent] = None


def get_rag_agent() -> RAGAgent:
    """获取 RAG Agent 全局实例"""
    global rag_agent
    if rag_agent is None:
        rag_agent = RAGAgent()
        rag_agent.initialize()
    return rag_agent
