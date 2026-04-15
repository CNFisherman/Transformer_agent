"""向量存储管理器"""
from pathlib import Path
from typing import List, Optional, Union
import pickle

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter

from config.settings import settings
from src.embedding import embedding_manager


class VectorStoreManager:
    """向量存储管理器"""

    def __init__(self):
        self.embeddings = embedding_manager.get_embeddings()
        self.vectorstore: Optional[FAISS] = None
        self.index_path = settings.INDEX_PATH / "faiss_index"

    def create_vectorstore(self, documents: List[Document]) -> FAISS:
        """从文档创建向量存储"""
        # 文本分块
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""]
        )

        chunks = text_splitter.split_documents(documents)
        print(f"文档分块完成: {len(documents)} 文档 -> {len(chunks)} 块")

        # 创建向量存储
        self.vectorstore = FAISS.from_documents(
            documents=chunks,
            embedding=self.embeddings
        )

        print(f"向量存储创建完成，共 {len(chunks)} 个向量")

        return self.vectorstore

    def save(self, path: Optional[Union[str, Path]] = None) -> Path:
        """保存向量存储到磁盘"""
        if self.vectorstore is None:
            raise ValueError("向量存储未初始化")

        save_path = Path(path) if path else self.index_path
        save_path.mkdir(parents=True, exist_ok=True)

        self.vectorstore.save_local(str(save_path))
        print(f"向量存储已保存到: {save_path}")

        # 保存元数据
        metadata_path = save_path / "metadata.pkl"
        metadata = {
            "doc_count": self.vectorstore.index.ntotal,
            "embedding_model": settings.EMBEDDING_MODEL
        }
        with open(metadata_path, "wb") as f:
            pickle.dump(metadata, f)

        return save_path

    def load(self, path: Optional[Union[str, Path]] = None) -> FAISS:
        """从磁盘加载向量存储"""
        load_path = Path(path) if path else self.index_path

        if not load_path.exists():
            raise FileNotFoundError(f"向量存储不存在: {load_path}")

        self.vectorstore = FAISS.load_local(
            str(load_path),
            self.embeddings,
            allow_dangerous_deserialization=True
        )

        print(f"向量存储加载完成: {self.vectorstore.index.ntotal} 个向量")

        return self.vectorstore

    def exists(self, path: Optional[Union[str, Path]] = None) -> bool:
        """检查向量存储是否存在"""
        load_path = Path(path) if path else self.index_path
        index_file = load_path / "index.faiss"
        return index_file.exists()
