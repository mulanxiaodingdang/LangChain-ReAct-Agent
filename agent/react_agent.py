"""ReAct Agent — 多意图、状态感知、7 工具、流式输出、三层记忆"""
import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Generator

from langgraph.prebuilt import create_react_agent
from langgraph.errors import GraphRecursionError
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser

from model.factory import chat_model
from utils.path_tool import get_abs_path
from utils.logger_handler import logger

from agent.intent_router import IntentRouter, Intent
from agent.retrieval_state import AgentRetrievalState
from agent.execution_policy import AgentExecutionPolicy
from agent.memory_manager import ShortTermMemory, CumulativeSummary, FactStore
from agent.tool_wrappers import TOOL_BUDGET_EXHAUSTED, KB_SEARCH_BLOCKED, INVALID_MARKERS
from agent.tools.agent_tools import (
    academic_search, search_academic_papers, fetch_paper_metadata,
    fetch_citation_info, compare_papers, mark_paper_not_in_kb,
    start_literature_review, _set_shared_state,
)
from agent.tools.middleware import AgentCallback


@dataclass
class EvidenceItem:
    """单条证据项：逐 subject 的证据收集结果"""
    subject: str
    content: str
    source: str  # "local" / "local_retry" / "online" / "online_fallback" / "duplicate"
    is_missing: bool = False
    is_soft_miss: bool = False
    quality: dict = field(default_factory=dict)
    chunks: list = field(default_factory=list)  # raw Document chunks from local retrieval


class ReactAgent:
    def __init__(self):
        self.callback = AgentCallback()

        # 记忆系统
        self.memory = ShortTermMemory()
        self.summary = CumulativeSummary()
        self.fact_store = FactStore()

        # 意图路由
        self.intent_router = IntentRouter()

        # per-execution 状态（在 execute_stream 中重置）
        self._retrieval_state: AgentRetrievalState | None = None
        self._retrieval_state_ref: list = [None]
        self._execution_policy: AgentExecutionPolicy | None = None
        self._policy_holder: list = [None]
        self._current_intent: Intent = Intent.QA

        # 工具列表（不做函数包装，预算/在线门控在工具内部检查）
        self.tools = [
            academic_search, search_academic_papers, fetch_paper_metadata,
            fetch_citation_info, compare_papers, mark_paper_not_in_kb,
            start_literature_review,
        ]

        # state_modifier callable — 动态选择 prompt + 终止检测
        def _prompt_fn(state: dict) -> list[SystemMessage]:
            for msg in state.get("messages", []):
                content = getattr(msg, "content", "") or ""
                if isinstance(content, str) and "__REVIEW_MODE__:" in content:
                    self._current_intent = Intent.REVIEW
                    break
            policy = self._policy_holder[0]
            if policy is not None:
                policy.round_counter += 1
            existing = list(state.get("messages", []))
            msgs = [SystemMessage(content=self._load_prompt(self._current_intent))]
            if policy is not None and policy.should_stop():
                policy.stop_yielded = True
                msgs.append(SystemMessage(content="STOP: 信息收集完毕，请直接回答用户问题。不要调用更多工具。"))
            return msgs + existing

        self.agent = create_react_agent(
            model=chat_model,
            tools=self.tools,
            state_modifier=_prompt_fn,
        )

    def _load_prompt(self, intent: Intent) -> str:
        file_map = {
            Intent.QA: "prompts/academic_main.txt",
            Intent.COMPARE: "prompts/paper_comparison.txt",
            Intent.REVIEW: "prompts/review.txt",
        }
        path = get_abs_path(file_map.get(intent, file_map[Intent.QA]))
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    # ── KB Missing 索引 ──

    _kb_missing_cache: dict | None = None

    def _load_kb_missing_papers(self) -> dict:
        if self._kb_missing_cache is not None:
            return self._kb_missing_cache
        path = get_abs_path("data/kb_missing_papers.json")
        if not os.path.exists(path):
            self._kb_missing_cache = {}
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._kb_missing_cache = data.get("papers", {})
        return self._kb_missing_cache

    def _match_kb_missing(self, subject: str) -> dict | None:
        papers = self._load_kb_missing_papers()
        if not papers:
            return None
        subj_lower = subject.strip().lower()
        for key, paper in papers.items():
            display = (paper.get("display_name") or "").lower()
            if subj_lower in key or key in subj_lower or subj_lower in display:
                return paper
            for alias in paper.get("aliases", []):
                if subj_lower in alias.lower() or alias.lower() in subj_lower:
                    return paper
        return None

    # ── Candidate Extraction ──

    def _extract_candidates(self, query: str) -> list[str]:
        prompt = (
            "从以下用户问题中提取所有论文名、方法名、系统名，每行一个。"
            "如果没有明确名称，输出 NONE。\n"
            f"问题：{query}\n输出："
        )
        raw = ""
        for chunk in chat_model.stream(prompt, config={"callbacks": [self.callback]}):
            if chunk.content and isinstance(chunk.content, str):
                raw += chunk.content
        candidates = [t.strip() for t in raw.strip().split("\n") if t.strip() and t.strip().upper() != "NONE"]
        logger.info(f"[Candidates] {candidates}")
        return candidates

    def _llm_rewrite_query(self, query: str) -> str:
        prompt = (
            "以下问题在英文学术论文库中检索不到相关内容，请将问题改写为不同的英文学术检索关键词。"
            "只输出改写后的检索词，不要解释。\n"
            f"原问题：{query}\n改写："
        )
        rewritten = ""
        for chunk in chat_model.stream(prompt):
            if chunk.content and isinstance(chunk.content, str):
                rewritten += chunk.content
        return rewritten.strip()

    # ── COMPARE: 对比维度提取 + 逐 subject 证据判断 ──

    def _extract_compare_aspects(self, query: str) -> str:
        """从用户对比问题中提取核心对比维度（英文关键词），仅 COMPARE 调用一次"""
        prompt = (
            "从以下用户问题中提取所有对比维度，输出对应的英文学术关键词（空格分隔，不超过 8 个词）。\n"
            "如：攻击目标→attack goal target；攻击手段→attack method technique；威胁模型→threat model\n"
            f"问题：{query}\n关键词："
        )
        aspects = ""
        for chunk in chat_model.stream(prompt, config={"callbacks": [self.callback]}):
            if chunk.content and isinstance(chunk.content, str):
                aspects += chunk.content
        result = aspects.strip()
        logger.info(f"[CompareAspects] {result}")
        return result

    def _judge_subject_evidence(self, docs: list, subject: str, aspects: str) -> dict:
        """逐 subject 判断：是否命中目标论文 + 证据是否覆盖对比维度 + 缺失信息 + 改写建议"""
        if not docs:
            return {"sufficient": False, "paper_hit": False, "missing_dimensions": "",
                    "refine_query": f"{subject} {aspects}"}

        chunks_text = ""
        for i, doc in enumerate(docs[:8], 1):
            meta = doc.metadata
            title = meta.get("paper_title", "?")
            section = meta.get("section", "?")
            ps = meta.get("page_start") or meta.get("page")
            pe = meta.get("page_end") or meta.get("page")
            page = f"p.{ps}" if ps == pe else f"pp.{ps}-{pe}"
            chunks_text += f"[{i}] 《{title}》| {section} | {page}\n{doc.page_content[:500]}\n\n"

        prompt = (
            f"论文名：{subject}\n"
            f"对比维度：{aspects}\n\n"
            f"检索到的片段：\n{chunks_text}\n"
            "请判断：\n"
            f"1. 是否命中了目标论文「{subject}」的原文？（PAPER_HIT: YES/NO）\n"
            "2. 相关片段是否足够覆盖对比维度？逐一检查每个维度是否有证据。（SUFFICIENT 或 INSUFFICIENT: 缺少xxx维度）\n"
            "3. 如不足，给出英文改写检索词（REFINE_QUERY: xxx）\n"
        )

        judgment = ""
        for chunk in chat_model.stream(prompt, config={"callbacks": [self.callback]}):
            if chunk.content and isinstance(chunk.content, str):
                judgment += chunk.content

        paper_hit = "PAPER_HIT: YES" in judgment.upper() or "PAPER_HIT:YES" in judgment.upper()
        sufficient = "SUFFICIENT" in judgment.upper() and "INSUFFICIENT" not in judgment.upper()

        m_missing = re.search(r"INSUFFICIENT:\s*(.+?)(?:\n|$)", judgment, re.IGNORECASE)
        missing_dimensions = m_missing.group(1).strip() if m_missing else ""

        m_refine = re.search(r"REFINE_QUERY:\s*(.+?)(?:\n|$)", judgment, re.IGNORECASE)
        refine_query = m_refine.group(1).strip() if m_refine else f"{subject} {aspects}"

        return {
            "sufficient": sufficient,
            "paper_hit": paper_hit,
            "missing_dimensions": missing_dimensions,
            "refine_query": refine_query,
        }

    # ── LLM Chunk Judge ──

    def _llm_judge_chunks(self, chunks: list, query: str) -> Generator[dict, None, dict]:
        """LLM 逐 chunk 判断相关性 + 充分性 + 生成 refine_query"""
        if not chunks:
            yield {"type": "text", "content": "[系统] 未检索到任何 chunk", "name": "system"}
            return {"sufficient": False, "relevant_chunks": [], "refine_query": query, "judgment": ""}

        chunks_text = ""
        for i, doc in enumerate(chunks, 1):
            meta = doc.metadata
            title = meta.get("paper_title", "?")
            section = meta.get("section", "?")
            ps = meta.get("page_start") or meta.get("page")
            pe = meta.get("page_end") or meta.get("page")
            page = f"p.{ps}" if ps == pe else f"pp.{ps}-{pe}"
            chunks_text += f"[{i}] 《{title}》| {section} | {page}\n{doc.page_content}\n\n"

        prompt = (
            "你是一个严格的检索质量评估器。请逐个检查以下检索到的论文片段是否与用户问题相关。\n\n"
            f"用户问题：{query}\n\n"
            "检索片段：\n"
            f"{chunks_text}\n"
            "请完成以下任务：\n"
            "1. 逐个判断每个片段是否与问题相关，输出格式：[N] [相关]/[不相关] — 一句话理由\n"
            "2. 综合判断：相关片段是否足够回答用户问题？输出：SUFFICIENT 或 INSUFFICIENT:<缺少什么信息>\n"
            "3. 如果 INSUFFICIENT，提供一个改写后的英文检索查询，输出：REFINE_QUERY: <english_query>\n"
        )

        judgment = ""
        for chunk in chat_model.stream(prompt, config={"callbacks": [self.callback]}):
            if chunk.content and isinstance(chunk.content, str):
                judgment += chunk.content

        sufficient = "SUFFICIENT" in judgment.upper() and "INSUFFICIENT" not in judgment.upper()

        relevant_indices: set[int] = set()
        for m in re.finditer(r"\[(\d+)\]\s*\[相关\]", judgment):
            relevant_indices.add(int(m.group(1)))

        relevant_chunks = [chunks[i - 1] for i in sorted(relevant_indices) if 1 <= i <= len(chunks)]

        refine_query = query
        m_refine = re.search(r"REFINE_QUERY:\s*(.+?)(?:\n|$)", judgment, re.IGNORECASE)
        if m_refine:
            refine_query = m_refine.group(1).strip()

        return {
            "sufficient": sufficient,
            "relevant_chunks": relevant_chunks if relevant_chunks else chunks,
            "refine_query": refine_query,
            "judgment": judgment,
        }

    # ── Generate Answer from Raw Chunks ──

    def _generate_answer_from_chunks(
        self, chunks: list, query: str, intent: Intent, extra_context: str = "",
        max_chunks: int = 0, max_tokens: int = 5000
    ) -> Generator[dict, None, None]:
        """从 raw chunks 构建带完整元数据的上下文，生成答案。
        max_chunks=0 表示不限制条数。max_tokens 控制上下文整体 token 上限（~2 chars/token 估算）。"""
        if not chunks and not extra_context:
            yield {"type": "text", "content": "[系统] 无可用检索结果", "name": "system"}
            return

        # 条数上限
        ctx_chunks = chunks[:max_chunks] if max_chunks > 0 else chunks

        # 构建每条 chunk 的完整元数据
        lines: list[str] = []
        for i, doc in enumerate(ctx_chunks, 1):
            meta = doc.metadata
            title = meta.get("paper_title", "未知")
            section = meta.get("section", "未知")
            ps = meta.get("page_start") or meta.get("page")
            pe = meta.get("page_end") or meta.get("page")
            if ps and pe:
                page = f"p.{ps}" if ps == pe else f"pp.{ps}-{pe}"
            else:
                page = "未知"
            lines.append(f"[{i}] 来源：《{title}》；章节：{section}；页码：{page}；内容：{doc.page_content}")

        context = "\n\n".join(lines)

        if extra_context:
            context += f"\n\n---\n{extra_context}"

        # 整体截断：超出 max_tokens 估算字符数时从末尾截断
        char_limit = max_tokens * 2
        if len(context) > char_limit:
            # 在 char_limit 附近找最近的 chunk 分隔符（双换行）
            cut = context.rfind("\n\n", 0, char_limit)
            if cut < 0 or cut < char_limit * 0.6:
                cut = char_limit
            context = context[:cut] + "\n\n...[上下文超出 token 限制，后续内容已截断]"
            logger.info(f"[Truncate] 上下文截断于 ~{cut} chars, limit={char_limit}")

        system_msg = SystemMessage(content=self._load_prompt(intent))
        user_msg = HumanMessage(content=f"用户问题：{query}\n\n检索结果：\n{context}")

        collected_text: list[str] = []
        for chunk in chat_model.stream([system_msg, user_msg], config={"callbacks": [self.callback]}):
            if chunk.content and isinstance(chunk.content, str):
                collected_text.append(chunk.content)
                yield {"type": "text", "content": chunk.content, "name": "assistant"}

        final_text = "".join(collected_text)

        # 引用校验
        max_n = len(ctx_chunks)
        cited = set(int(m) for m in re.findall(r"\[(\d+)\]", final_text))
        invalid = sorted(n for n in cited if n < 1 or n > max_n)
        if invalid:
            yield {"type": "text", "content": f"\n\n> 引用校验警告：无效引用 {invalid}，有效范围 [1-{max_n}]。", "name": "system"}

        # 有证据但零引用 → 警告
        if max_n > 0 and not cited:
            logger.warning("[Citation] 有 chunk 但回答零引用")
            yield {"type": "text", "content": "\n\n> 引用校验警告：回答未引用任何证据编号，请忽略以上回答并重新提问。", "name": "system"}
            return

        # 占位符检测
        if any(re.search(pat, final_text) for pat in [r"\[N\]", r"\[n\]", r"\[数字\]", r"\[编号\]", r"\[\?\]"]):
            logger.warning("[Placeholder] 检测到占位符引用")
            yield {"type": "text", "content": "\n[系统提示] 回答中包含无效引用占位符，已拦截。\n", "name": "system"}
            return

        # 记忆更新
        if final_text.strip():
            self.memory.add_turn(query, final_text)
            if self.memory.should_compress():
                recent = "\n".join(m["content"][:300] for m in self.memory.buffer[-8:])
                self.summary.update(recent, chat_model)
            total_turns = self.memory.turn_count()
            if total_turns > 0 and total_turns % FactStore.EXTRACT_INTERVAL == 0:
                new_facts = self.fact_store.extract_facts(self.memory.buffer)
                if new_facts:
                    self.fact_store.add_facts("research", new_facts)

    # ── Shared Evidence Layer ──

    def _collect_evidence_for_subject(
        self, subject: str, query: str, guards: dict
    ) -> Generator[dict, None, EvidenceItem]:
        from rag.rag_service import RagSummarizeService
        rag = RagSummarizeService()

        search_query = query  # 始终用原始 query 检索，不用 subject

        # Guard 3: 防重复
        if search_query in guards["queries_issued"]:
            logger.info(f"[Evidence] 重复 query，跳过: {search_query}")
            return EvidenceItem(subject=subject, content="", source="duplicate")
        guards["queries_issued"].add(search_query)

        # Step 0: 预检 KB 缺失索引
        missing = self._match_kb_missing(subject if subject else query)
        if missing:
            online_q = missing.get("online_query") or missing.get("display_name", search_query)
            online_result = search_academic_papers.invoke({"query": online_q})
            self.callback.tool_invocation_log.append({
                "name": "search_academic_papers", "output": online_result,
                "elapsed": 0, "status": "success",
            })
            guards["online_done"] = True
            yield {"type": "tool", "content": online_result[:200], "name": "search_academic_papers"}
            display = missing.get("display_name", subject)
            context = f"[在线检索] 论文「{display}」不在本地 KB 中：\n{online_result}"
            if missing.get("abstract"):
                context += f"\n\n预存元数据：摘要={missing['abstract'][:300]}..."
            return EvidenceItem(subject=subject, content=context, source="online", is_missing=True)

        # Guard 1: 本地 KB 已禁用 → 交给调用方决定是否在线
        if guards["local_kb_disabled"]:
            logger.info(f"[Evidence] 本地 KB 已禁用，跳过: {search_query}")
            return EvidenceItem(subject=subject, content="", source="local_disabled", is_soft_miss=True)

        # Step 1: 第一次本地检索 → 返回原始 chunks
        try:
            docs1 = rag.retriever_docs(search_query)
        except Exception as e:
            logger.warning(f"[Evidence] 本地检索失败: {e}")
            docs1 = []

        quality1 = rag._check_retrieval_quality(search_query, docs1)
        preview1 = docs1[0].page_content[:200] if docs1 else ""
        self.callback.tool_invocation_log.append({
            "name": "academic_search", "output": preview1,
            "elapsed": 0, "status": "success",
        })
        yield {"type": "tool", "content": preview1, "name": "academic_search"}
        logger.info(
            f"[Quality] subject={subject} soft_miss={quality1['is_soft_miss']} "
            f"signals={quality1.get('signals', {})}"
        )

        if not quality1["is_soft_miss"]:
            return EvidenceItem(subject=subject, content="", source="local",
                              quality=quality1, chunks=docs1)

        # 软 miss → 改写 query 再试一次
        guards["miss_count"] = guards.get("miss_count", 0) + 1
        rewritten = self._llm_rewrite_query(search_query)
        if rewritten and rewritten not in guards["queries_issued"]:
            guards["queries_issued"].add(rewritten)
            try:
                docs2 = rag.retriever_docs(rewritten)
            except Exception as e:
                logger.warning(f"[Evidence] 改写检索失败: {e}")
                docs2 = []

            quality2 = rag._check_retrieval_quality(rewritten, docs2)
            preview2 = docs2[0].page_content[:200] if docs2 else ""
            self.callback.tool_invocation_log.append({
                "name": "academic_search", "output": preview2,
                "elapsed": 0, "status": "success",
            })
            yield {"type": "tool", "content": preview2, "name": "academic_search"}

            if not quality2["is_soft_miss"]:
                return EvidenceItem(subject=subject, content="", source="local_retry",
                                  quality=quality2, chunks=docs2)

        # 连续两次软 miss → 禁用本地 KB
        guards["miss_count"] = guards.get("miss_count", 0) + 1
        if guards["miss_count"] >= 2:
            guards["local_kb_disabled"] = True
            logger.warning(f"[Guard] 本地 KB 已禁用，miss_count={guards['miss_count']}")

        # 返回软 miss（chunks 仍保留，供调用方 LLM judge 二次判断）
        return EvidenceItem(subject=subject, content="", source="local",
                          is_soft_miss=True, quality=quality1, chunks=docs1)

    # ── QA Pipeline (三轮：本地检索 → LLM judge → refine → judge → 在线兜底) ──

    def _execute_qa_pipeline(self, query: str) -> Generator[dict, None, None]:
        from rag.rag_service import RagSummarizeService
        rag = RagSummarizeService()

        candidates = self._extract_candidates(query)
        subject = candidates[0] if candidates else ""

        all_chunks: list = []
        online_context = ""
        issued: set[str] = set()

        # Step 0: KB 缺失预检
        missing = self._match_kb_missing(subject if subject else query)
        if missing:
            online_q = missing.get("online_query") or missing.get("display_name", query)
            online_result = search_academic_papers.invoke({"query": online_q})
            self.callback.tool_invocation_log.append({
                "name": "search_academic_papers", "output": online_result,
                "elapsed": 0, "status": "success",
            })
            yield {"type": "tool", "content": online_result[:200], "name": "search_academic_papers"}
            display = missing.get("display_name", subject)
            online_context = f"[在线检索] 论文「{display}」不在本地 KB 中：\n{online_result}"
            if missing.get("abstract"):
                online_context += f"\n\n预存元数据：摘要={missing['abstract'][:300]}..."
            yield from self._generate_answer_from_chunks([], query, Intent.QA, extra_context=online_context, max_chunks=15, max_tokens=5000)
            return

        # Round 1: 本地检索
        issued.add(query)
        try:
            docs1 = rag.retriever_docs(query)
        except Exception:
            docs1 = []
        preview1 = docs1[0].page_content[:200] if docs1 else ""
        self.callback.tool_invocation_log.append({
            "name": "academic_search", "output": preview1, "elapsed": 0, "status": "success",
        })
        yield {"type": "tool", "content": preview1, "name": "academic_search"}

        all_chunks = list(docs1)

        # Round 1: LLM judge
        judge1 = yield from self._llm_judge_chunks(all_chunks, query)
        if judge1["sufficient"]:
            yield from self._generate_answer_from_chunks(judge1["relevant_chunks"], query, Intent.QA, max_chunks=15, max_tokens=5000)
            self._log_session_end("qa")
            return

        # Round 2: refine query 再检索
        refine_query = judge1.get("refine_query", query)
        if refine_query and refine_query != query and refine_query not in issued:
            issued.add(refine_query)
            try:
                docs2 = rag.retriever_docs(refine_query)
            except Exception:
                docs2 = []
            preview2 = docs2[0].page_content[:200] if docs2 else ""
            self.callback.tool_invocation_log.append({
                "name": "academic_search", "output": preview2, "elapsed": 0, "status": "success",
            })
            yield {"type": "tool", "content": preview2, "name": "academic_search"}

            # 去重合并
            seen = {d.page_content[:120] for d in all_chunks}
            for d in docs2:
                if d.page_content[:120] not in seen:
                    all_chunks.append(d)
                    seen.add(d.page_content[:120])

        # Round 2: 再次 judge
        judge2 = yield from self._llm_judge_chunks(all_chunks, query)
        if judge2["sufficient"]:
            yield from self._generate_answer_from_chunks(judge2["relevant_chunks"], query, Intent.QA, max_chunks=15, max_tokens=5000)
            self._log_session_end("qa")
            return

        # Round 3: 在线兜底
        online_result = search_academic_papers.invoke({"query": query})
        self.callback.tool_invocation_log.append({
            "name": "search_academic_papers", "output": online_result, "elapsed": 0, "status": "success",
        })
        yield {"type": "tool", "content": online_result[:200], "name": "search_academic_papers"}
        online_context = f"[在线检索补充]\n{online_result}"

        yield from self._generate_answer_from_chunks(
            judge2["relevant_chunks"], query, Intent.QA, extra_context=online_context, max_chunks=15, max_tokens=5000
        )
        self._log_session_end("qa")

    def _log_session_end(self, intent_name: str):
        tools_count = len(self.callback.tool_invocation_log)
        logger.warning(f"[SessionEnd] intent={intent_name} tools={tools_count}")

    # ── COMPARE Pipeline (逐 subject 检索 → 独立 judge → 两轮上限 → 15 chunk 均衡分配) ──

    def _execute_compare_pipeline(self, query: str) -> Generator[dict, None, None]:
        from rag.rag_service import RagSummarizeService
        rag = RagSummarizeService()

        candidates = self._extract_candidates(query)
        if not candidates:
            yield from self._execute_qa_pipeline(query)
            return

        # 提取对比维度（所有 subject 共用）
        aspects = self._extract_compare_aspects(query)

        all_chunks: list = []
        online_contexts: list[str] = []
        subject_chunk_count: dict[str, int] = {}  # 记录每个 subject 已有 chunk 数

        for subject in candidates[:4]:
            subject_chunk_count[subject] = 0

            # Step 0: KB 缺失预检
            missing = self._match_kb_missing(subject)
            if missing:
                online_q = missing.get("online_query") or missing.get("display_name", subject)
                online_result = search_academic_papers.invoke({"query": online_q})
                self.callback.tool_invocation_log.append({
                    "name": "search_academic_papers", "output": online_result,
                    "elapsed": 0, "status": "success",
                })
                yield {"type": "tool", "content": online_result[:200], "name": "search_academic_papers"}
                display = missing.get("display_name", subject)
                ctx = f"[在线] 「{display}」不在本地 KB：\n{online_result}"
                if missing.get("abstract"):
                    ctx += f"\n摘要：{missing['abstract'][:300]}"
                online_contexts.append(ctx)
                continue

            # Round 1: subject + aspects 检索
            search_query = f"{subject} {aspects}"
            try:
                docs1 = rag.retriever_docs(search_query)
            except Exception:
                docs1 = []
            preview1 = docs1[0].page_content[:200] if docs1 else ""
            self.callback.tool_invocation_log.append({
                "name": "academic_search", "output": preview1, "elapsed": 0, "status": "success",
            })
            yield {"type": "tool", "content": preview1, "name": "academic_search"}

            # 逐 subject judge
            judge = self._judge_subject_evidence(docs1, subject, aspects)
            logger.info(
                f"[SubjectJudge] {subject} paper_hit={judge['paper_hit']} "
                f"sufficient={judge['sufficient']} missing={judge['missing_dimensions']}"
            )

            if judge["sufficient"]:
                seen = {d.page_content[:120] for d in all_chunks}
                for d in docs1:
                    if d.page_content[:120] not in seen:
                        all_chunks.append(d)
                        seen.add(d.page_content[:120])
                        subject_chunk_count[subject] += 1
                continue

            # 未命中目标论文 → 在线检索
            if not judge["paper_hit"]:
                online_result = search_academic_papers.invoke({"query": subject})
                self.callback.tool_invocation_log.append({
                    "name": "search_academic_papers", "output": online_result,
                    "elapsed": 0, "status": "success",
                })
                yield {"type": "tool", "content": online_result[:200], "name": "search_academic_papers"}
                online_contexts.append(f"[在线] 「{subject}」本地检索未命中：\n{online_result}")
                continue

            # 命中但证据不足 → Round 2: 改写重试
            refine_q = judge.get("refine_query", f"{subject} {aspects}")
            try:
                docs2 = rag.retriever_docs(refine_q)
            except Exception:
                docs2 = []
            preview2 = docs2[0].page_content[:200] if docs2 else ""
            self.callback.tool_invocation_log.append({
                "name": "academic_search", "output": preview2, "elapsed": 0, "status": "success",
            })
            yield {"type": "tool", "content": preview2, "name": "academic_search"}

            # 合并两轮 chunk（去重），不再 judge，硬上限已到
            seen = {d.page_content[:120] for d in all_chunks}
            for d in docs1 + docs2:
                if d.page_content[:120] not in seen:
                    all_chunks.append(d)
                    seen.add(d.page_content[:120])
                    subject_chunk_count[subject] += 1

        if not all_chunks and not online_contexts:
            yield {"type": "text", "content": "[系统] 未检索到任何相关文献。", "name": "system"}
            return

        # 均衡分配：每 subject 保留 3-5 条，总数不超过 15
        capped = self._balance_chunks_by_subject(all_chunks, subject_chunk_count, max_total=15, min_per=3, max_per=5)
        logger.info(f"[Compare] chunk 分配: {subject_chunk_count} → capped={len(capped)}")

        # 统一 LLM judge
        judge_result = yield from self._llm_judge_chunks(capped, query)

        # compare_papers 辅助结构化对比
        compare_text = ""
        if len(candidates) >= 2:
            try:
                compare_text = compare_papers.invoke({"titles_str": "; ".join(candidates[:4])})
                self.callback.tool_invocation_log.append({
                    "name": "compare_papers", "output": compare_text,
                    "elapsed": 0, "status": "success",
                })
                yield {"type": "tool", "content": compare_text[:200], "name": "compare_papers"}
            except Exception as e:
                logger.warning(f"[Compare] compare_papers 失败: {e}")

        extra = "\n\n".join(online_contexts)
        if compare_text:
            extra = compare_text + ("\n\n" + extra if extra else "")

        yield from self._generate_answer_from_chunks(
            judge_result["relevant_chunks"], query, Intent.COMPARE,
            extra_context=extra, max_chunks=15, max_tokens=5000
        )
        self._log_session_end("compare")

    def _balance_chunks_by_subject(
        self, chunks: list, counts: dict[str, int], max_total: int, min_per: int, max_per: int
    ) -> list:
        """按 subject 均衡分配 chunk：每 subject 保留 min_per~max_per 条，总数不超过 max_total"""
        if len(chunks) <= max_total:
            return chunks

        # 按 subject 关键词匹配分组
        subject_keys = list(counts.keys())
        groups: dict[str, list] = {k: [] for k in subject_keys}
        unassigned: list = []

        for doc in chunks:
            title = (doc.metadata.get("paper_title", "") or "").lower()
            matched = None
            for subj in subject_keys:
                if subj.lower() in title:
                    matched = subj
                    break
            if matched:
                groups[matched].append(doc)
            else:
                unassigned.append(doc)

        result = []
        remaining = max_total

        # 第一轮：每个 subject 分配 min_per 条
        for subj in subject_keys:
            take = min(min_per, len(groups[subj]), remaining)
            result.extend(groups[subj][:take])
            remaining -= take

        # 第二轮：有余额则补充到 max_per
        for subj in subject_keys:
            if remaining <= 0:
                break
            already = min(min_per, len(groups[subj]))
            extra = min(max_per - already, len(groups[subj]) - already, remaining)
            if extra > 0:
                result.extend(groups[subj][already:already + extra])
                remaining -= extra

        # 仍有余额 → 补充未分配 chunk
        if remaining > 0 and unassigned:
            result.extend(unassigned[:remaining])

        return result

    # ── REVIEW Pipeline (raw chunks → judge → 在线补充) ──

    def _execute_review_pipeline(self, query: str) -> Generator[dict, None, None]:
        from rag.rag_service import RagSummarizeService
        rag = RagSummarizeService()

        # 1. 本地检索 → 原始 chunks
        try:
            docs = rag.retriever_docs(query)
        except Exception:
            docs = []
        preview = docs[0].page_content[:200] if docs else ""
        self.callback.tool_invocation_log.append({
            "name": "academic_search", "output": preview, "elapsed": 0, "status": "success",
        })
        yield {"type": "tool", "content": preview, "name": "academic_search"}

        # 2. LLM judge chunks
        judge_result = yield from self._llm_judge_chunks(docs, query)

        # 3. 不足则在线补充
        extra_context = ""
        if not judge_result["sufficient"]:
            online_result = search_academic_papers.invoke({"query": query})
            self.callback.tool_invocation_log.append({
                "name": "search_academic_papers", "output": online_result, "elapsed": 0, "status": "success",
            })
            yield {"type": "tool", "content": online_result[:200], "name": "search_academic_papers"}
            extra_context = f"[在线检索补充]\n{online_result}"

        yield from self._generate_answer_from_chunks(
            judge_result["relevant_chunks"], query, Intent.REVIEW, extra_context=extra_context, max_chunks=30, max_tokens=8000
        )
        self._log_session_end("review")

    def execute_stream(self, query: str) -> Generator[dict, None, None]:
        # === RESET per-execution state ===
        self._retrieval_state = AgentRetrievalState()
        self._retrieval_state_ref[0] = self._retrieval_state
        self._execution_policy = AgentExecutionPolicy()
        self._policy_holder[0] = self._execution_policy
        self._current_intent = Intent.QA
        self.callback.tool_invocation_log.clear()

        # 向工具模块注入共享状态（预算计数器 + 在线门控引用）
        tool_budget = [0]
        _set_shared_state(tool_budget, self._retrieval_state_ref)

        # === CLASSIFY intent ===
        self._current_intent = self.intent_router.classify(query)
        yield {"type": "intent", "content": self._current_intent.value, "name": "system"}

        # === ROUTE by intent ===
        if self._current_intent == Intent.QA:
            yield from self._execute_qa_pipeline(query)
            self._policy_holder[0] = None
            return
        elif self._current_intent == Intent.COMPARE:
            yield from self._execute_compare_pipeline(query)
            self._policy_holder[0] = None
            return
        elif self._current_intent == Intent.REVIEW:
            yield from self._execute_review_pipeline(query)
            self._policy_holder[0] = None
            return

        # === BUILD initial messages (fallback: should not reach here) ===
        summary_msg = self.summary.get_summary_message()
        system_msgs = []
        if summary_msg:
            system_msgs.append(summary_msg)

        history = self.memory.get_recent_turns()
        input_messages = system_msgs + history + [{"role": "user", "content": query}]

        # === REACT LOOP ===
        collected_text: list[str] = []
        tool_results_all: list[dict] = []
        round_has_effective = False
        tool_count_this_round = 0

        try:
            for chunk, metadata in self.agent.stream(
                {"messages": input_messages},
                stream_mode="messages",
                config={"callbacks": [self.callback]},
            ):
                node = metadata.get("langgraph_node", "")

                if node == "agent" and hasattr(chunk, "content") and chunk.content:
                    # 模型文本输出
                    content = chunk.content
                    if isinstance(content, str):
                        collected_text.append(content)
                        yield {"type": "text", "content": content, "name": "assistant"}

                elif node == "tools" and hasattr(chunk, "content"):
                    # 工具结果
                    tool_name = getattr(chunk, "name", "unknown")
                    tool_content = chunk.content if chunk.content else ""

                    if isinstance(tool_content, list):
                        tool_content = str(tool_content)

                    tool_count_this_round += 1

                    yield {
                        "type": "tool",
                        "content": tool_content[:200] if isinstance(tool_content, str) else str(tool_content)[:200],
                        "name": tool_name,
                    }

                    is_valid = not any(m in tool_content for m in INVALID_MARKERS)
                    tool_results_all.append({
                        "name": tool_name,
                        "content": tool_content,
                        "is_valid": is_valid,
                    })

                    if is_valid:
                        round_has_effective = True

        except GraphRecursionError:
            logger.warning("[ReactAgent] Graph recursion limit reached")
            yield {"type": "text", "content": "\n[检索轮次已达上限，基于已有信息回答]\n", "name": "system"}

        # === ROUND EFFECTIVENESS (post-loop) ===
        if round_has_effective:
            self._execution_policy.mark_round_effective()
        elif tool_count_this_round > 0:
            self._execution_policy.mark_round_empty()

        # === NO-TOOL-CALL DETECTION (兜底: 模型模拟伪检索时不写入记忆) ===
        stats = self.callback.get_round_stats()
        if stats["total_tool_calls"] == 0:
            final_text = "".join(collected_text)
            logger.warning(
                f"[NoToolCall] intent={self._current_intent.value} "
                f"text={final_text[:200]}"
            )
            yield {"type": "text", "content": "\n[系统提示] 未检测到工具调用，请重新提问。\n", "name": "system"}
            self._policy_holder[0] = None
            return

        # === CITATION VERIFICATION ===
        final_text = "".join(collected_text)
        citation_warning = self._verify_citations(final_text, tool_results_all)
        if citation_warning:
            yield {"type": "text", "content": citation_warning, "name": "system"}

        # === PLACEHOLDER DETECTION (兜底: 模型照抄 Prompt 中的占位符) ===
        placeholder_patterns = [r"\[N\]", r"\[n\]", r"\[数字\]", r"\[编号\]", r"\[\?\]"]
        placeholder_hits = []
        for pat in placeholder_patterns:
            if re.search(pat, final_text):
                placeholder_hits.append(pat)
        if placeholder_hits:
            logger.warning(f"[Placeholder] 检测到占位符引用: {placeholder_hits}")
            yield {"type": "text", "content": "\n[系统提示] 回答中包含无效引用占位符，已拦截。请重新提问。\n", "name": "system"}
            self._policy_holder[0] = None
            return

        # === MEMORY UPDATES ===
        if final_text.strip():
            self.memory.add_turn(query, final_text)

            if self.memory.should_compress():
                recent = "\n".join(
                    m["content"][:300] for m in self.memory.buffer[-8:]
                )
                self.summary.update(recent, chat_model)

            total_turns = self.memory.turn_count()
            if total_turns > 0 and total_turns % FactStore.EXTRACT_INTERVAL == 0:
                new_facts = self.fact_store.extract_facts(self.memory.buffer)
                if new_facts:
                    self.fact_store.add_facts("research", new_facts)

        # === SESSION LOG ===
        stats = self.callback.get_round_stats()
        logger.warning(
            f"[SessionEnd] intent={self._current_intent.value} "
            f"rounds={self._execution_policy.round_counter} "
            f"tools={stats['total_tool_calls']}/{stats['successful']}/{stats['errors']} "
            f"empty={self._execution_policy.empty_rounds_consecutive}"
        )

        # Cleanup
        self._policy_holder[0] = None

    def _verify_citations(self, answer: str, tool_results: list) -> str:
        """校验回答中的 [N] 引用编号"""
        acad_results = [r for r in tool_results if r["name"] == "academic_search" and r["is_valid"]]
        if not acad_results:
            return ""

        max_valid = 0
        for r in acad_results:
            content = r.get("content", "")
            cited = set(int(m) for m in re.findall(r"\[(\d+)\]", content) if m.isdigit())
            if cited:
                max_valid = max(max_valid, max(cited))

        if max_valid == 0:
            return ""

        cited_in_answer = set(int(m) for m in re.findall(r"\[(\d+)\]", answer) if m.isdigit())
        invalid = sorted(n for n in cited_in_answer if n > max_valid)
        if invalid:
            return f"\n\n> 引用校验警告：发现无效引用编号 {invalid}，有效范围为 [1-{max_valid}]。"
        return ""


if __name__ == "__main__":
    agent = ReactAgent()
    print("=== ReAct Agent 测试 ===\n")
    for chunk in agent.execute_stream("Transformer模型的核心机制是什么？"):
        if chunk["type"] == "text":
            print(chunk["content"], end="", flush=True)
        elif chunk["type"] == "tool":
            print(f"\n[工具: {chunk['name']}] {chunk['content'][:100]}...")
        elif chunk["type"] == "intent":
            print(f"[意图: {chunk['content']}]")
    print("\n\n=== Done ===")
