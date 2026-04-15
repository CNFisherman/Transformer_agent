"""Text 文档加载器"""
from pathlib import Path
from typing import List, Union
from langchain_core.documents import Document


class TextLoader:
    """文本文件加载器"""

    def __init__(self, encoding: str = "utf-8"):
        self.encoding = encoding

    def load(self, file_path: Union[str, Path]) -> List[Document]:
        """加载单个文本文件"""
        file_path = Path(file_path)

        with open(file_path, "r", encoding=self.encoding) as f:
            content = f.read()

        # 尝试确定文档标题（从文件名）
        title = file_path.stem

        metadata = {
            "source": str(file_path),
            "title": title,
            "file_type": file_path.suffix
        }

        return [Document(page_content=content, metadata=metadata)]

    def load_directory(self, directory: Union[str, Path], extensions: List[str] = None) -> List[Document]:
        """加载目录下所有文本文件"""
        if extensions is None:
            extensions = [".txt", ".md", ".rst"]

        directory = Path(directory)
        documents = []

        for ext in extensions:
            for text_file in directory.rglob(f"*{ext}"):
                try:
                    docs = self.load(text_file)
                    documents.extend(docs)
                    print(f"[OK] 加载: {text_file.name}")
                except Exception as e:
                    print(f"[FAIL] 加载失败 {text_file.name}: {e}")

        return documents
