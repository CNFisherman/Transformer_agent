"""LLM 聊天管理器"""
from typing import Optional, List, Dict
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from config.settings import settings


class ChatManager:
    """LLM 聊天管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 检测是否使用 Ollama
        if "localhost" in settings.OPENAI_API_BASE:
            self.llm = ChatOllama(
                model=settings.OPENAI_MODEL,
                base_url=settings.OPENAI_API_BASE.replace("/v1", ""),  # Ollama 不需要 /v1
                temperature=0.7,
                streaming=False
            )
        else:
            self.llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_API_BASE,
                temperature=0.7,
                streaming=False
            )

        self._initialized = True

    def chat(self, message: str, system_prompt: Optional[str] = None) -> str:
        """简单对话"""
        messages = []

        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        messages.append(HumanMessage(content=message))

        response = self.llm.invoke(messages)
        return response.content

    def chat_with_history(self, message: str, history: List[Dict[str, str]], system_prompt: Optional[str] = None) -> str:
        """带历史的对话"""
        messages = []

        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        # 添加历史消息
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        # 添加当前消息
        messages.append(HumanMessage(content=message))

        response = self.llm.invoke(messages)
        return response.content


# 全局单例
chat_manager = ChatManager()
