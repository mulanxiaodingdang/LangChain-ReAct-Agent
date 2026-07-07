<div align="center">

# LangChain ReAct Agent · 科研论文问答系统

**基于 LangChain + ReAct 范式 + RAG 检索增强的科研论文智能问答系统**

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
&nbsp;
[![LangChain](https://img.shields.io/badge/LangChain-0.3-green)](https://www.langchain.com/)
&nbsp;
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange)](https://github.com/langchain-ai/langgraph)
&nbsp;
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40-red)](https://streamlit.io/)
&nbsp;
[![License](https://img.shields.io/badge/License-MIT-yellow)](./LICENSE)

</div>

---

## 项目简介

基于 LangChain 框架实现的 **ReAct（Reasoning + Acting）Agent**，集成 RAG 检索增强。系统能根据用户提出的学术问题，从论文向量库中检索相关内容，自主推理并生成专业回答，通过 Streamlit 流式界面实时展示 Agent 的思考与检索过程。

## 技术架构

<div align="center">

```
用户输入 (Streamlit)
      │
      ▼
┌─────────────────────────────────────────┐
│            ReAct Agent                   │
│                                          │
│  ┌──────────┐    ┌──────────────────┐   │
│  │ Thought  │───→│     Action       │   │
│  │ (推理)    │    │  (论文检索/RAG)   │   │
│  └──────────┘    └────────┬─────────┘   │
│       ↑                   │              │
│       └─── Observation ◄──┘              │
│                                          │
│   Middleware: 工具监控 · 模型调用日志      │
└─────────────────────────────────────────┘
      │                
      ▼                
┌──────────┐
│   RAG    │
│  Chroma  │
│ 向量检索  │
└──────────┘
```

</div>

### 核心特性

| 特性 | 说明 |
|---|---|
| **ReAct 范式** | Thought → Action → Observation 循环，Agent 自主推理并决定何时检索论文 |
| **RAG 检索增强** | Chroma 向量库 + SiliconFlow Embedding，MD5 文件去重，支持 txt/pdf 论文加载 |
| **流式对话界面** | Streamlit 构建，支持流式逐字输出、历史消息留存、Agent 推理过程可见 |
| **模块化结构** | Agent / RAG / Model / Tools / Middleware 独立模块，配置 YAML 驱动 |

## 技术栈

| 层级 | 技术 |
|---|---|
| LLM | 通义千问（SiliconFlow / OpenAI 兼容 API） |
| Agent 框架 | LangChain + LangGraph |
| 向量数据库 | Chroma |
| 文档处理 | PyPDF + RecursiveCharacterTextSplitter |
| 前端 | Streamlit |
| 配置 | YAML 驱动（Agent / RAG / Chroma / Prompts） |

## 快速开始

### 环境要求

- **Python** ≥ 3.10
- **SiliconFlow API Key**（[硅基流动](https://cloud.siliconflow.cn/account/ak) 申请）

### 1. 克隆仓库

```bash
git clone https://github.com/lhh737/LangChain-ReAct-Agent.git
cd LangChain-ReAct-Agent
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API Key

参考 `.env.example`，设置硅基流动 API Key：

```bash
# Linux / macOS
export SILICONFLOW_API_KEY="your-api-key"

# Windows (CMD)
set SILICONFLOW_API_KEY=your-api-key
```

> 申请地址：[硅基流动控制台](https://cloud.siliconflow.cn/account/ak)

### 4. 初始化知识库（首次运行）

将论文 PDF 或 TXT 文件放入 `data/` 目录，然后执行：

```bash
python -c "from rag.vector_store import VectorStoreService; VectorStoreService().load_document()"
```

### 5. 启动应用

```bash
streamlit run app.py
```

浏览器自动打开 http://localhost:8501

### 验证运行

启动后在聊天框输入以下测试问题：

- *Transformer 模型的核心机制是什么？*
- *BERT 和 GPT 在架构上有哪些主要区别？*
- *请介绍一下注意力机制的原理*

## 项目结构

```
LangChain-ReAct-Agent/
│
├── agent/                          # Agent 核心
│   ├── react_agent.py              #   ReAct Agent 主逻辑（流式执行）
│   └── tools/
│       ├── agent_tools.py          #   工具函数（论文检索）
│       └── middleware.py           #   中间件（工具监控/模型调用日志）
│
├── rag/                            # RAG 检索增强
│   ├── vector_store.py             #   Chroma 向量库 · 文档加载 · MD5 去重
│   └── rag_service.py              #   RAG 检索 → LLM 总结服务
│
├── model/
│   └── factory.py                  # 模型工厂（ChatOpenAI + OpenAIEmbeddings）
│
├── config/                         # YAML 配置文件
│   ├── agent.yml                   #   Agent 行为配置
│   ├── chroma.yml                  #   向量库与检索参数
│   ├── prompts.yml                 #   提示词模板
│   └── rag.yml                     #   模型与参数
│
├── prompts/                        # 提示词模板
│   ├── main_prompt.txt             #   System Prompt
│   └── rag_summarize.txt           #   RAG 总结 Prompt
│
├── utils/                          # 工具函数
│   ├── config_handler.py           #   YAML 配置加载
│   ├── file_handler.py             #   文件解析（PDF/TXT）
│   ├── logger_handler.py           #   日志管理
│   ├── path_tool.py                #   路径工具
│   └── prompt_loader.py            #   提示词加载
│
├── data/                           # 知识库文档（论文 PDF/TXT）
├── app.py                          # Streamlit 应用入口
├── requirements.txt
└── README.md
```

## 配置说明

项目通过 `config/` 目录下的 YAML 文件统一管理配置：

| 文件 | 说明 |
|---|---|
| `rag.yml` | 对话模型名称、Embedding 模型名称 |
| `chroma.yml` | Chroma 持久化路径、分块大小、检索 Top-K、支持的文件类型 |
| `prompts.yml` | 提示词模板文件路径 |
| `agent.yml` | Agent 通用配置 |

首次运行只需确保 **SiliconFlow API Key 已设置** 且 `data/` 目录下有论文文档即可。

## License

MIT © [lhh737](https://github.com/lhh737)