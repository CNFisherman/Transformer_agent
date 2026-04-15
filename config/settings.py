"""全局配置文件"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class Settings:
    """应用配置"""

    # 项目根目录
    PROJECT_ROOT: Path = Path(__file__).parent.parent

    # LLM 配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    # Embedding 配置
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")

    # 向量存储
    VECTOR_STORE_TYPE: str = os.getenv("VECTOR_STORE_TYPE", "faiss")
    VECTOR_STORE_PATH: Path = PROJECT_ROOT / os.getenv("VECTOR_STORE_PATH", "./data/vectorstore")

    # 文档路径
    DOCUMENTS_PATH: Path = PROJECT_ROOT / os.getenv("DOCUMENTS_PATH", "./documents/raw")
    INDEX_PATH: Path = PROJECT_ROOT / os.getenv("INDEX_PATH", "./data/index")

    # API 配置
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # RAG 配置
    TOP_K: int = 4  # 检索返回的文档数
    CHUNK_SIZE: int = 1000  # 文档分块大小
    CHUNK_OVERLAP: int = 200  # 分块重叠大小

    def ensure_dirs(self):
        """确保必要目录存在"""
        self.VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)
        self.INDEX_PATH.mkdir(parents=True, exist_ok=True)
        self.DOCUMENTS_PATH.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
