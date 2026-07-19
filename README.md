<div align="center">

# PaperMind-科研论文问答系统

**基于 LangChain + ReAct 范式 + RAG 检索增强的科研论文智能问答 Agent**

</div>

---

## 项目简介

多意图、状态感知的科研论文智能问答 Agent。系统根据用户问题自动识别意图（问答 / 对比 / 综述），通过 **本地 RAG 检索 + 在线学术搜索** 双通道获取证据，经 LLM 推理后生成带引用编号的专业回答。前端提供 Streamlit 流式界面，实时展示工具调用、检索来源和推理过程。

### 核心能力

- **本地知识库检索**：Chroma 向量库 + BM25 关键词 + Reranker 精排，混合检索论文全文片段
- **在线学术搜索**：arXiv / OpenAlex / DBLP / Crossref / Semantic Scholar 五源聚合，三阶段管线（候选精确匹配 → 关键词消歧 → 改写变体兜底）
- **身份感知验证**：DOI / arXiv ID / 标题 / 作者 / 年份 多信号交叉验证，四级置信度（EXACT → HIGH → MEDIUM → LOW）
- **自动知识库补全**：在线检索到的论文自动写入缺失索引，下次查询直接复用预存元数据

## 技术架构

```
用户输入 (Streamlit)
      │
      ▼
┌──────────────────────────────────────────────────────┐
│                   IntentRouter                        │
│          QA / COMPARE / REVIEW 三意图分类              │
└──────────────────────────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────────────────────────┐
│                 ReAct Agent (LangGraph)               │
│                                                       │
│  ┌─────────┐   ┌─────────┐   ┌──────────────────┐   │
│  │ Thought │──→│ Action  │──→│   Observation    │   │
│  │ (推理)   │   │ (7工具)  │   │ (检索结果/元数据)  │   │
│  └─────────┘   └─────────┘   └──────────────────┘   │
│                                                       │
│  Middleware: 工具调用日志 · Token 统计 · 轮次有效性    │
└──────────────────────────────────────────────────────┘
      │                           │
      ▼                           ▼
┌──────────────┐    ┌────────────────────────────┐
│  本地 RAG     │    │     在线检索管线              │
│              │    │                              │
│ Chroma 向量库 │    │ ┌─────┐ ┌─────┐ ┌─────┐   │
│ + BM25 关键词 │    │ │Stage1│→│Stage2│→│Stage3│   │
│ + Reranker   │    │ │候选精确│ │+关键词│ │改写变体│   │
│              │    │ └─────┘ └─────┘ └─────┘   │
└──────────────┘    │                              │
                    │ PaperIdentityValidator       │
                    │ CompositeRanker (身份+语义)   │
                    └────────────────────────────┘
      │                           │
      ▼                           ▼
┌──────────────────────────────────────────────────────┐
│                    三层记忆系统                        │
│  ShortTermMemory (4轮缓冲) · CumulativeSummary (LLM压缩) │
│  · FactStore (每3轮提取长期事实)                        │
└──────────────────────────────────────────────────────┘
```

### 7 工具一览

| 工具 | 类型 | 功能 |
|---|---|---|
| `academic_search` | 本地 | Chroma + BM25 + Reranker 混合检索论文全文片段，返回带 `[N]` 编号的内容 |
| `search_academic_papers` | 在线 | 五源学术数据库聚合搜索，自动构建 SearchIntent 走三阶段管线 |
| `fetch_paper_metadata` | 在线 | 精确标题 → 作者 / 年份 / DOI / 期刊 / 摘要 / 链接 |
| `fetch_citation_info` | 在线 | 精确标题 → 引用计数 |
| `compare_papers` | 聚合 | 多篇论文（2-4 篇）并行检索本地 KB + 在线元数据，结构化对比 |
| `mark_paper_not_in_kb` | 持久 | 标记论文为本地知识库缺失，后续自动跳过本地检索 |
| `start_literature_review` | 模式 | 触发文献综述模式，Agent 切换为广泛检索 + 分类归纳 |

## 技术栈

| 层级 | 技术 |
|---|---|
| LLM | DeepSeek-V3.2 / 通义千问（SiliconFlow API） |
| Embedding | BGE-M3（SiliconFlow API） |
| Agent 框架 | LangChain 0.3 + LangGraph 0.2 |
| 向量数据库 | Chroma 0.5 |
| 关键词检索 | BM25（rank-bm25 + jieba 分词） |
| 文档处理 | PyPDF + RecursiveCharacterTextSplitter |
| 在线检索 | httpx 异步 → arXiv / OpenAlex / DBLP / Crossref / Semantic Scholar |
| 前端 | Streamlit 1.40 流式对话 + 工具面板 |
| 配置 | YAML 驱动（6 个配置文件） |

## 快速开始

### 环境要求

- **Python** ≥ 3.10
- **OpenAI 兼容 API**（SiliconFlow / DeepSeek / OpenAI / vLLM 等任一即可）

### 1. 克隆仓库

```bash
git clone https://github.com/mulanxiaodingdang/LangChain-ReAct-Agent.git
cd LangChain-ReAct-Agent
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 API Key 等信息
```

系统通过 OpenAI 兼容 API 调用 LLM 和 Embedding 模型，支持任意兼容服务商。

| 变量 | 说明 | 默认值 |
|---|---|---|
| `LLM_MODEL` | 对话模型名称 | `deepseek-ai/DeepSeek-V3.2` |
| `LLM_BASE_URL` | LLM API 地址 | `https://api.siliconflow.cn/v1` |
| `LLM_API_KEY` | LLM API 密钥 | — |
| `EMBED_MODEL` | Embedding 模型名称 | `BAAI/bge-m3` |
| `EMBED_BASE_URL` | Embedding API 地址 | `https://api.siliconflow.cn/v1` |
| `EMBED_API_KEY` | Embedding API 密钥 | — |
| `LLM_TIMEOUT` | 调用超时（秒） | `120` |
| `LLM_MAX_RETRIES` | 最大重试次数 | `3` |

LLM 和 Embedding 可分别使用不同的服务商。模型名称需与对应 API 支持的名称一致。

**常见配置示例：**

```bash
# SiliconFlow（默认）
LLM_MODEL=deepseek-ai/DeepSeek-V3.2
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_API_KEY=sk-xxxxxxxxxxxxxxxx

# DeepSeek 官方 API
LLM_MODEL=deepseek-chat
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=sk-xxxxxxxxxxxxxxxx

# OpenAI 官方 API
LLM_MODEL=gpt-4o
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-xxxxxxxxxxxxxxxx

# 本地 vLLM / Ollama
LLM_MODEL=qwen2.5-72b
LLM_BASE_URL=http://localhost:8000/v1
LLM_API_KEY=not-needed
```

向后兼容：未设置上述变量时，系统会自动回退读取 `SILICONFLOW_API_KEY` 环境变量和 `config/rag.yml` 中的模型名。

### 4. 初始化知识库

将论文 PDF 或 TXT 文件放入 `data/` 目录，然后依次执行：

**Step 1 — 入库**：从 `data/` 读取 PDF/TXT，结构化解析、分块、MD5 去重后写入 Chroma 向量库。

```bash
python -c "from rag.vector_store import VectorStoreService; VectorStoreService().load_document()"
```

**Step 2 — 建索引**：从 Chroma 向量库读取全部文档，构建 BM25 关键词索引 + 缩写索引 + 文档清单（混合检索需要）。

```bash
python -c "from rag.rag_service import RagSummarizeService; RagSummarizeService().rebuild_bm25_index()"
```

> 每次新增或替换 `data/` 目录下的论文文件后，都需要重新执行以上两步。缺少 Step 2 会导致混合检索退化为纯向量检索。

### 5. 启动应用

```bash
streamlit run app.py
```

浏览器访问 http://localhost:8501

### 测试示例

| 意图 | 问题示例 |
|---|---|
| QA | "Transformer 模型的核心机制是什么？" |
| QA | "ELSA3D 解决了计算机视觉领域的什么问题？" |
| COMPARE | "BERT 和 GPT 在架构上有哪些主要区别？" |
| COMPARE | "对比 FlippedRAG 和传统 RAG 在安全性上的差异" |
| REVIEW | "LLM 安全领域的攻击与防御研究现状综述" |

## 项目结构

```
LangChain-ReAct-Agent/
│
├── agent/                              # Agent 核心模块
│   ├── react_agent.py                  #   ReAct Agent 主逻辑（流式执行 · 三种Pipeline · 证据收集）
│   ├── intent_router.py                #   意图分类器（QA/COMPARE/REVIEW）
│   ├── execution_policy.py             #   执行策略（预算控制 · 空轮终止）
│   ├── memory_manager.py               #   三层记忆（短期缓冲 · 累积摘要 · 长期事实）
│   ├── retrieval_state.py              #   检索状态机（miss计数 · 本地KB禁用 · 质量信号）
│   ├── tool_wrappers.py                #   工具包装器（预算门控 / 在线结果门控 / 日志）
│   │
│   ├── retrieval/                      #   在线检索子系统
│   │   ├── academic_client.py          #     五源学术数据聚合客户端 · SearchIntent · 缓存
│   │   ├── retrieval_pipeline.py       #     三阶段检索管线（候选 → 消歧 → 改写兜底）
│   │   ├── composite_ranker.py         #     组合排序器（身份 + 语义双评分）
│   │   ├── paper_validator.py          #     身份感知验证器（DOI/arXiv/标题/作者/年份多信号）
│   │   └── query_rewrite.py            #     查询改写器（规则 + 同义词扩展）
│   │
│   └── tools/                          #   Agent 工具
│       ├── agent_tools.py              #     7 工具定义 + 自动索引
│       └── middleware.py               #     AgentCallback（工具/LLM调用日志）
│
├── rag/                                # RAG 检索增强
│   ├── vector_store.py                 #   Chroma 向量库 · 文档加载 · MD5 去重
│   ├── rag_service.py                  #   RAG 检索 → LLM 总结 · 检索质量检测
│   ├── bm25_store.py                   #   BM25 关键词索引 · 中文分词
│   ├── retrieval_strategy.py           #   检索策略（混合检索 · RRF 融合 · Reranker）
│   ├── topic_analyzer.py               #   领域主题分析
│   ├── paper_metadata.py               #   论文元数据解析
│   └── paper_parser.py                 #   论文结构解析
│
├── model/
│   └── factory.py                      # 模型工厂（ChatOpenAI + OpenAIEmbeddings）
│
├── config/                             # YAML 配置文件
│   ├── rag.yml                         #   对话模型 · Embedding 模型
│   ├── chroma.yml                      #   Chroma 路径 · 分块参数 · Top-K
│   ├── prompts.yml                     #   提示词模板路径
│   ├── agent.yml                       #   Agent 行为配置
│   ├── reranker.yml                    #   Reranker 模型配置
│   ├── acronyms.yml                    #   缩写词词典
│   └── domain_terms.yml                #   领域术语词典
│
├── prompts/                            # 提示词模板
│   ├── academic_main.txt               #   默认 QA 意图 System Prompt
│   ├── paper_comparison.txt            #   对比分析 Prompt
│   ├── review.txt                      #   文献综述 Prompt
│   └── rag_summarize.txt               #   RAG 总结 Prompt
│
├── app_pages/                          # Streamlit 页面
│   └── chat_page.py                    #   对话页面（流式输出 · 工具面板 · 记忆管理）
│
├── utils/                              # 工具函数
│   ├── config_handler.py               #   YAML 配置加载
│   ├── file_handler.py                 #   文件解析（PDF/TXT）
│   ├── logger_handler.py               #   日志管理
│   ├── path_tool.py                    #   路径工具
│   └── prompt_loader.py                #   提示词加载
│
├── evaluation/                         # 评估模块
│   ├── evaluator.py                    #   评估主逻辑
│   ├── test_questions.yml              #   评估问题集
│   └── reports/                        #   评估报告
│
├── data/                               # 数据目录
│   ├── cache/                          #   在线检索缓存（per-source TTL）
│   ├── kb_missing_papers.json          #   KB 缺失论文索引（自动补全）
│   ├── short_term_memory.json          #   短期记忆持久化
│   └── long_term_facts.json            #   长期事实存储
│
├── app.py                              # Streamlit 应用入口
├── requirements.txt
└── README.md
```

## 系统工作流

### 意图路由

```
用户问题 → IntentRouter.classify()
  ├─ 含 "vs/compare/对比/异同" → COMPARE
  ├─ 含 "review/survey/综述/发展脉络" → REVIEW
  └─ 其他 → QA
```

### QA 管线（三轮检索）

```
Round 1: 本地 Chroma+BM25+Reranker 检索 → LLM judge 充分性
  ├─ SUFFICIENT → 生成回答 + 引用校验
  └─ INSUFFICIENT →
Round 2: LLM 改写 query → 二次本地检索 → LLM judge
  ├─ SUFFICIENT → 生成回答
  └─ INSUFFICIENT →
Round 3: 在线学术检索（三阶段管线）
  Stage 1: candidate-only 精确匹配 → 身份验证 → 早停
  Stage 2: candidate + 消歧关键词
  Stage 3: 规则改写变体兜底
  → 合并在线结果生成回答
```

### 在线检索三阶段管线

```
SearchIntent(candidate, candidate_type, keyword, fallback_query)
  │
  ├─ Stage 1: candidate 精确搜索 → 身份验证 EXACT/HIGH → 早停
  ├─ Stage 2: candidate + keyword 消歧搜索
  └─ Stage 3: fallback_query 改写变体搜索（最多3个变体）
```

### 身份感知验证（6 层多信号）

```
Tier 1: DOI / arXiv ID 全标识符并行精确匹配 → EXACT
Tier 2: 从 query 提取作者姓氏 + 年份
Tier 3: 标题匹配（acronym 字母验证 · 全文相似度）
Tier 4: 作者 + 年份交叉信号（±1 年容差）
Tier 5: 多信号共识决策（标题 + 作者 + 年份加权）
Tier 6: 分数兜底（match_score 阈值）
```

## 配置说明

首次运行只需设置 `SILICONFLOW_API_KEY` 环境变量，并将论文文档放入 `data/` 目录。

| 配置文件 | 说明 |
|---|---|
| `config/rag.yml` | LLM 模型名称、Embedding 模型名称 |
| `config/chroma.yml` | Chroma 持久化路径、chunk 大小、检索 Top-K、支持文件类型 |
| `config/prompts.yml` | 各意图对应的 Prompt 模板路径 |
| `config/agent.yml` | Agent 通用行为配置 |
| `config/reranker.yml` | Reranker 模型与参数 |
| `config/acronyms.yml` | 论文缩写词映射词典 |
| `config/domain_terms.yml` | 领域术语扩展词典 |

## 数据持久化

| 文件 | 说明 |
|---|---|
| `data/kb_missing_papers.json` | KB 缺失论文索引，在线检索命中后自动写入元数据（标题/作者/摘要/DOI 等） |
| `data/short_term_memory.json` | 短期对话记忆（最近 4 轮），每次对话后自动更新 |
| `data/long_term_facts.json` | 长期事实提取（每 3 轮），分类存储研究进展 |
| `data/cache/*.json` | 在线检索缓存，按 SourceQuerySpec 生成 key，per-source TTL |


