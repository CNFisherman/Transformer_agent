"""Embedding 管理器 - 支持 Ollama"""
from langchain_openai import OpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings
from config.settings import settings
import os


class EmbeddingManager:
    """Embedding 管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 获取 embedding 专用的 base URL
        embedding_base = os.getenv("EMBEDDING_BASE", "")

        # 如果配置了独立的 embedding base（本地 Ollama），使用 OllamaEmbeddings
        if embedding_base:
            self.embeddings = OllamaEmbeddings(
                model=settings.EMBEDDING_MODEL,
                base_url=embedding_base
            )
        else:
            # 否则使用云端 OpenAI 兼容接口
            self.embeddings = OpenAIEmbeddings(
                model=settings.EMBEDDING_MODEL,
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_API_BASE
            )

        self._initialized = True

    def get_embeddings(self):
        """获取 embeddings 实例"""
        return self.embeddings


# 全局单例
embedding_manager = EmbeddingManager()
