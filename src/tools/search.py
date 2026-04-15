"""网络搜索工具（占位）"""
from langchain_core.tools import tool


@tool
def web_search_tool(query: str) -> str:
    """
    搜索互联网获取最新信息。

    Args:
        query: 搜索关键词

    Returns:
        搜索结果摘要
    """
    # TODO: 集成真实搜索 API (如 SerpAPI, DuckDuckGo 等)
    return f"[占位] 搜索: {query}\n\n注意: 请配置真实的搜索 API"


# LangChain tool 格式
web_search = web_search_tool
