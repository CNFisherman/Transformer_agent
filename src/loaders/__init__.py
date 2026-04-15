"""Document Loaders"""
from .pdf_loader import PDFLoader
from .txt_loader import TextLoader
from .doc_loader import DocxLoader

__all__ = ["PDFLoader", "TextLoader", "DocxLoader"]
