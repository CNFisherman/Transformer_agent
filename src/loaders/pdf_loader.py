"""PDF 文档加载器"""
from pathlib import Path
from typing import List, Union
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader


class PDFLoader:
    """PDF 文档加载器"""

    def __init__(self):
        pass

    def load(self, file_path: Union[str, Path]) -> List[Document]:
        """加载单个 PDF 文件"""
        loader = PyPDFLoader(str(file_path))
        return loader.load()

    def load_directory(self, directory: Union[str, Path]) -> List[Document]:
        """加载目录下所有 PDF 文件"""
        directory = Path(directory)
        documents = []

        for pdf_file in directory.rglob("*.pdf"):
            try:
                docs = self.load(pdf_file)
                documents.extend(docs)
                print(f"[OK] 加载: {pdf_file.name}")
            except Exception as e:
                print(f"[FAIL] 加载失败 {pdf_file.name}: {e}")

        return documents
