# Enterprise AI Agent - 企业智能体

基于 RAG 的企业内部文档问答系统，支持知识库检索和工具调用。

## 技术栈

- **语言**: Python 3.10+
- **核心框架**: LangChain + LlamaIndex
- **向量数据库**: FAISS / Chroma (本地)
- **大模型**: OpenAI GPT / 本地模型 (如 Ollama)
- **API**: FastAPI

## 项目结构

```
enterprise-agent/
├── config/                 # 配置文件
│   ├── __init__.py
│   ├── settings.py         # 全局设置
│   └── prompts.py          # Prompt 模板
├── documents/              # 文档目录
│   ├── raw/                # 原始文档
│   └── processed/          # 处理后的文档
├── src/
│   ├── __init__.py
│   ├── loaders/            # 文档加载器
│   │   ├── __init__.py
│   │   ├── pdf_loader.py
│   │   ├── txt_loader.py
│   │   └── doc_loader.py
│   ├── embedding/          # 向量化模块
│   │   ├── __init__.py
│   │   └── embeddings.py
│   ├── vectorstore/        # 向量存储
│   │   ├── __init__.py
│   │   └── faiss_store.py
│   ├── retriever/          # 检索器
│   │   ├── __init__.py
│   │   └── retriever.py
│   ├── llm/                # LLM 模块
│   │   ├── __init__.py
│   │   └── chat.py
│   ├── agent/              # Agent 核心
│   │   ├── __init__.py
│   │   └── rag_agent.py
│   └── tools/              # 工具集
│       ├── __init__.py
│       ├── search.py
│       └── calculator.py
├── api/                    # API 接口
│   ├── __init__.py
│   ├── main.py             # FastAPI 主入口
│   └── routes/
│       ├── __init__.py
│       └── chat.py         # 对话接口
├── scripts/                # 脚本
│   ├── ingest.py           # 文档 ingestion 脚本
│   └── test_chat.py        # 测试脚本
├── tests/                  # 测试
├── .env.example            # 环境变量示例
├── requirements.txt
└── README.md
```

## 学习路径

1. **阶段一：基础 RAG**
   - [x] 文档加载与处理
   - [x] 向量化与存储
   - [x] 检索与问答

2. **阶段二：工具调用**
   - [ ] 添加搜索工具
   - [ ] 添加计算工具
   - [ ] Tool calling 实践

3. **阶段三：Agent 进阶**
   - [ ] ReAct 模式
   - [ ] 多工具协作
   - [ ] 记忆系统

4. **阶段四：多 Agent**
   - [ ] Agent 协作
   - [ ] 工作流编排
   - [ ] 企业系统集成

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填写你的 API Key
```

### 3. 加载文档

```bash
python scripts/ingest.py --path ./documents/raw
```

### 4. 启动 API

```bash
uvicorn api.main:app --reload --port 8000
```

### 5. 测试问答

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "公司有哪些规章制度？"}'
```

## License

MIT
