"""计算器工具"""
from langchain_core.tools import tool


@tool
def calculator_tool(expression: str) -> str:
    """
    执行数学计算。

    Args:
        expression: 数学表达式，如 "2 + 2", "10 * 5", "sqrt(16)", "100 / 3"

    Returns:
        计算结果
    """
    try:
        # 安全评估数学表达式
        allowed_chars = set("0123456789+-*/(). sqrt三角函数sin cos tan log")
        if any(c not in allowed_chars for c in expression):
            return "错误: 表达式包含非法字符"

        # 使用 eval 进行计算（仅用于演示，生产环境请使用安全解析器）
        result = eval(expression)
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"
