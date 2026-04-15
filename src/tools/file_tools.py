"""文件管理工具"""
from pathlib import Path
from langchain_core.tools import tool
from config.settings import settings


@tool
def list_files_tool(extension: str = None) -> str:
    """
    列出文档目录中的所有文件。

    Args:
        extension: 可选，按文件扩展名过滤，如 ".docx", ".pdf", ".txt" 等

    Returns:
        文件列表
    """
    if not settings.DOCUMENTS_PATH.exists():
        return "文档目录不存在或为空。"

    files = []
    try:
        for item in settings.DOCUMENTS_PATH.rglob("*"):
            if item.is_file():
                rel_path = str(item.relative_to(settings.DOCUMENTS_PATH))
                if extension is None or item.suffix.lower() == extension.lower():
                    files.append(rel_path)
    except Exception as e:
        return f"读取文件列表失败: {str(e)}"

    if not files:
        return "未找到任何文件。"

    # 按类型分组
    if extension is None:
        by_type = {}
        for f in files:
            ext = Path(f).suffix.lower()
            if ext not in by_type:
                by_type[ext] = []
            by_type[ext].append(f)

        result = "文档目录中的所有文件：\n\n"
        for ext, file_list in sorted(by_type.items()):
            result += f"【{ext or '无扩展名'} 文件】（共 {len(file_list)} 个）：\n"
            for f in sorted(file_list):
                result += f"  - {f}\n"
            result += "\n"
        return result
    else:
        result = f"文档目录中的 {extension} 文件（共 {len(files)} 个）：\n\n"
        for f in sorted(files):
            result += f"  - {f}\n"
        return result


@tool
def list_word_files() -> str:
    """
    列出文档目录中所有的 Word 文件（包括 .doc 和 .docx 格式）。

    Returns:
        Word 文件列表
    """
    if not settings.DOCUMENTS_PATH.exists():
        return "文档目录不存在或为空。"

    docx_files = []
    doc_files = []

    try:
        for item in settings.DOCUMENTS_PATH.rglob("*"):
            if item.is_file():
                rel_path = str(item.relative_to(settings.DOCUMENTS_PATH))
                if item.suffix.lower() == ".docx":
                    docx_files.append(rel_path)
                elif item.suffix.lower() == ".doc":
                    doc_files.append(rel_path)
    except Exception as e:
        return f"读取文件列表失败: {str(e)}"

    result = "Word 文件列表：\n\n"

    if docx_files:
        result += f"【.docx 格式】（共 {len(docx_files)} 个）：\n"
        for f in sorted(docx_files):
            result += f"  - {f}\n"
        result += "\n"

    if doc_files:
        result += f"【.doc 格式（旧版）】（共 {len(doc_files)} 个）：\n"
        for f in sorted(doc_files):
            result += f"  - {f}\n"
        result += "\n"

    total = len(docx_files) + len(doc_files)
    if total == 0:
        return "文档目录中没有找到 Word 文件。"

    result += f"总计：{total} 个 Word 文件"
    return result


# LangChain tool 格式
list_files = list_files_tool
list_word = list_word_files
