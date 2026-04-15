"""文档 ingestion 脚本"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from src.loaders import PDFLoader, TextLoader, DocxLoader
from src.loaders.metadata_loader import MetadataLoader
from src.vectorstore import VectorStoreManager


def load_documents():
    """加载所有文档"""
    documents = []

    # 加载元数据
    print("\n=== 加载文档元数据 ===")
    metadata_loader = MetadataLoader(settings.DOCUMENTS_PATH)
    metadata_loader.print_summary()

    # PDF 文档
    print("\n=== 加载 PDF 文档 ===")
    pdf_loader = PDFLoader()
    pdf_docs = pdf_loader.load_directory(settings.DOCUMENTS_PATH)
    # 注入元数据
    for doc in pdf_docs:
        metadata_loader.enrich_document(doc)
    documents.extend(pdf_docs)

    # Word 文档
    print("\n=== 加载 Word 文档 ===")
    docx_loader = DocxLoader()
    docx_docs = docx_loader.load_directory(settings.DOCUMENTS_PATH)
    # 注入元数据
    for doc in docx_docs:
        metadata_loader.enrich_document(doc)
    documents.extend(docx_docs)

    # 文本文件
    print("\n=== 加载文本文件 ===")
    txt_loader = TextLoader()
    txt_docs = txt_loader.load_directory(settings.DOCUMENTS_PATH)
    # 注入元数据
    for doc in txt_docs:
        metadata_loader.enrich_document(doc)
    documents.extend(txt_docs)

    print(f"\n总计加载文档: {len(documents)} 个")
    return documents


def main():
    print("=" * 50)
    print("企业智能体 - 文档 ingestion")
    print("=" * 50)

    # 检查文档目录
    if not settings.DOCUMENTS_PATH.exists() or not any(settings.DOCUMENTS_PATH.iterdir()):
        print(f"\n警告: 文档目录为空: {settings.DOCUMENTS_PATH}")
        print("请将文档放入该目录后重试。")
        return

    # 加载文档
    documents = load_documents()

    if not documents:
        print("\n未找到任何文档！")
        return

    # 创建向量存储
    print("\n=== 创建向量存储 ===")
    vectorstore_manager = VectorStoreManager()
    vectorstore_manager.create_vectorstore(documents)

    # 保存向量存储
    print("\n=== 保存向量存储 ===")
    vectorstore_manager.save()

    print("\n" + "=" * 50)
    print("[OK] ingestion 完成！")
    print("=" * 50)
    print(f"向量存储路径: {settings.INDEX_PATH}")
    print(f"文档数量: {len(documents)}")


if __name__ == "__main__":
    main()
