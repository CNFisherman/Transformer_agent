"""测试问答脚本"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import RAGAgent


def main():
    print("=" * 50)
    print("西电济南变压器企业智能体 - 问答测试")
    print("=" * 50)

    # 初始化 Agent
    agent = RAGAgent()

    try:
        agent.initialize()
    except FileNotFoundError as e:
        print(f"\n错误: {e}")
        print("\n请先运行 ingestion 脚本加载文档:")
        print("  python scripts/ingest.py")
        return

    print("\n问答测试已启动（输入 'quit' 退出）")
    print("-" * 50)

    while True:
        question = input("\n问题: ").strip()

        if question.lower() in ["quit", "exit", "q"]:
            print("再见!")
            break

        if not question:
            continue

        print("\n检索中...")
        result = agent.query(question)

        print("\n回答:")
        print("-" * 50)
        print(result["answer"])

        print("\n来源文档:")
        print("-" * 50)
        for i, src in enumerate(result["sources"], 1):
            print(f"\n[{i}] {src['source']}")
            print(f"    {src['content'][:100]}...")


if __name__ == "__main__":
    main()
