"""在线检索管线：SearchIntent → Stage 1 → 身份验证 → 早停（Stage 2/3 预留）"""
from agent.retrieval.query_rewrite import RuleBasedRewriter
from agent.retrieval.academic_client import AcademicDataClient, SearchIntent
from agent.retrieval.composite_ranker import CompositeRanker
from agent.retrieval.paper_validator import PaperIdentityValidator, ConfidenceLevel
from utils.logger_handler import logger


class OnlineRetrievalPipeline:
    def __init__(self):
        self.rewriter = RuleBasedRewriter()
        self.client = AcademicDataClient()
        self.ranker = CompositeRanker()
        self.validator = PaperIdentityValidator()
        self._last_scored: list = []
        self._last_intent: SearchIntent | None = None
        self._stage_results: list = []       # 各阶段 SourceSearchResult
        self._early_stopped: bool = False
        self._stop_stage: int = 0

    # ── 带 SearchIntent 的检索（Commit 2: Stage 1 only）──

    def run_with_intent(self, intent: SearchIntent, max_results: int = 20) -> str:
        """三阶段检索入口：Stage 1 candidate-only → Stage 2 +keyword → Stage 3 fallback variants"""
        self._last_intent = intent
        self._stage_results = []
        self._early_stopped = False
        self._stop_stage = 0
        all_papers: list = []

        # ── Stage 1: candidate-only ──
        if intent.candidate:
            logger.info(f"[OnlinePipeline] Stage1 candidate={intent.candidate} type={intent.candidate_type}")
            stage1_results = self.client.search_stage(intent, stage=1, max_per_source=5)
            self._stage_results.extend(stage1_results)
            all_papers = self._collect_and_dedup(stage1_results)
            if all_papers:
                self._score_and_check_early_stop(intent, all_papers, stage=1)

        # ── Stage 2: candidate + disambiguation keyword ──
        if not self._early_stopped and intent.candidate:
            keyword = self._extract_disambiguation_keyword(intent)
            if keyword:
                intent.keyword = keyword
                logger.info(f"[OnlinePipeline] Stage2 candidate={intent.candidate} keyword={keyword}")
                stage2_results = self.client.search_stage(intent, stage=2, max_per_source=5)
                self._stage_results.extend(stage2_results)
                new_papers = self._collect_and_dedup(stage2_results)
                if new_papers:
                    all_papers = self._merge_papers(all_papers, new_papers)
                    self._score_and_check_early_stop(intent, all_papers, stage=2)

        # ── Stage 3: RuleBasedRewriter fallback variants ──
        if not self._early_stopped:
            fallback_q = intent.fallback_query or intent.candidate
            variants = self.rewriter.rewrite(fallback_q)
            logger.info(f"[OnlinePipeline] Stage3 variants={variants[:3]}")
            for variant in variants[:3]:
                if self._early_stopped:
                    break
                stage3_results = self.client.search_stage(
                    intent, stage=3, max_per_source=5, fallback_variant=variant)
                self._stage_results.extend(stage3_results)
                new_papers = self._collect_and_dedup(stage3_results)
                if new_papers:
                    all_papers = self._merge_papers(all_papers, new_papers)
                    self._score_and_check_early_stop(intent, all_papers, stage=3)

        # 返回格式化结果
        if not self._last_scored:
            return "未找到相关论文。"

        return self._format_results(self._last_scored)

    def _collect_and_dedup(self, stage_results: list) -> list:
        """从 SourceSearchResult 中提取 papers，跨源去重 + 元数据合并"""
        papers = []
        for r in stage_results:
            if r.status == "ok":
                papers.extend(r.papers)
        if not papers:
            return []
        from agent.retrieval.academic_client import AcademicDataClient
        return AcademicDataClient._merge_duplicates(papers)

    def _score_and_check_early_stop(self, intent: SearchIntent, all_papers: list, stage: int):
        """对 all_papers 做 identity + semantic 双评分 → 验证 → 更新 _last_scored → 早停判断"""
        identity_scores = self.ranker.rank_identity(intent.candidate, all_papers)
        semantic_scores = self.ranker._max_score(
            intent.fallback_query or intent.candidate, all_papers, self.ranker.rankers)

        combined = []
        for p, i_score, s_score in zip(all_papers, identity_scores, semantic_scores):
            level, reason = self.validator.validate(
                intent.candidate, p, i_score, intent.candidate_type)
            combined.append((p, i_score, s_score, level, reason))
            logger.info(
                f"[OnlinePipeline] Stage{stage} validate: {p.title[:80]} "
                f"id_score={i_score:.3f} sem_score={s_score:.3f} level={level.value}"
            )

        scored = [(p, 0.6 * i + 0.3 * s + 0.1) for p, i, s, _, _ in combined]
        scored.sort(key=lambda x: x[1], reverse=True)
        self._last_scored = scored

        for p, i_score, s_score, level, reason in combined:
            if level in (ConfidenceLevel.EXACT, ConfidenceLevel.HIGH):
                self._early_stopped = True
                self._stop_stage = stage
                logger.info(
                    f"[OnlinePipeline] Stage{stage} 早停: {p.title[:80]} "
                    f"level={level.value} reason={reason}"
                )
                break

    @staticmethod
    def _merge_papers(existing: list, new_papers: list) -> list:
        """合并论文列表，按标题去重"""
        seen = {p.title.lower().strip() for p in existing}
        merged = list(existing)
        for p in new_papers:
            key = p.title.lower().strip()
            if key not in seen:
                seen.add(key)
                merged.append(p)
        return merged

    @staticmethod
    def _extract_disambiguation_keyword(intent: SearchIntent) -> str:
        """从 fallback_query 中提取消歧关键词：移除 candidate 后取最长的英文词"""
        import re
        candidate = intent.candidate.lower().strip()
        fallback = (intent.fallback_query or "").lower().strip()
        if not fallback or fallback == candidate:
            return ""
        remaining = re.sub(re.escape(candidate), "", fallback, count=1).strip()
        # 提取所有纯英文词（>=3 字符），跳过常见停用词
        stop_words = {"the", "and", "for", "with", "based", "using", "via", "from",
                      "new", "3d", "2d", "all", "its", "can", "has", "one", "two"}
        english_words = re.findall(r'[a-z][a-z0-9]{2,}', remaining)
        candidates = [w for w in english_words if w not in stop_words]
        if not candidates:
            return ""
        # 优先最长词
        candidates.sort(key=len, reverse=True)
        return candidates[0]

    def _format_results(self, scored: list, max_output: int = 5) -> str:
        """格式化 scored papers 为文本输出"""
        valid = []
        for paper, score in scored:
            level, _ = self.validator.validate(
                self._last_intent.candidate if self._last_intent else "",
                paper, score, self._last_intent.candidate_type if self._last_intent else "unknown")
            if level in (ConfidenceLevel.EXACT, ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM):
                valid.append((paper, score, level))

        if not valid:
            top_score = f"{scored[0][1]:.2f}" if scored else "N/A"
            return f"未找到高置信度匹配论文（共检索到 {len(scored)} 条结果，最高分 {top_score}，均低于 0.70 阈值）。"

        lines = []
        for i, (paper, score, level) in enumerate(valid[:max_output]):
            authors = ", ".join(paper.authors[:2]) if paper.authors else ""
            year = f"({paper.year})" if paper.year else ""
            title = paper.title
            if len(title) > 100:
                title = title[:97] + "..."
            lines.append(f"[{i + 1}] {title} | {authors} {year} | {paper.source}")
            if paper.abstract:
                abstract_short = paper.abstract[:150].strip()
                lines.append(f"    摘要: {abstract_short}...")

        return "\n".join(lines)

    # ── 兼容旧接口 ──

    def run(self, query: str) -> str:
        """向后兼容：无 candidate 时走旧逻辑"""
        logger.info(f"[OnlinePipeline]原始query (legacy): {query}")

        variants = self.rewriter.rewrite(query)
        logger.info(f"[OnlinePipeline]query变体: {variants}")

        all_papers = self.client.search(query, max_results=20)

        if not all_papers:
            return "未找到相关论文。"

        scored = self.ranker.rank(query, all_papers)
        self._last_scored = scored

        for i, (paper, score) in enumerate(scored[:3]):
            logger.info(f"[OnlinePipeline] top{i+1}: score={score:.3f} title={paper.title[:80]}")

        return self._format_legacy(scored)

    def _format_legacy(self, scored: list, max_output: int = 5) -> str:
        valid: list[tuple] = []
        for paper, score in scored:
            level, _ = self.validator.validate("", paper, score)
            if level in (ConfidenceLevel.EXACT, ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM):
                valid.append((paper, score, level))

        if not valid:
            top_score = f"{scored[0][1]:.2f}" if scored else "N/A"
            return f"未找到高置信度匹配论文（共检索到 {len(scored)} 条结果，最高分 {top_score}，均低于 0.70 阈值）。"

        lines = []
        for i, (paper, score, level) in enumerate(valid[:max_output]):
            authors = ", ".join(paper.authors[:2]) if paper.authors else ""
            year = f"({paper.year})" if paper.year else ""
            title = paper.title
            if len(title) > 100:
                title = title[:97] + "..."
            lines.append(f"[{i + 1}] {title} | {authors} {year} | {paper.source}")
            if paper.abstract:
                abstract_short = paper.abstract[:150].strip()
                lines.append(f"    摘要: {abstract_short}...")

        return "\n".join(lines)

    def fetch_metadata_by_title(self, title: str) -> dict | None:
        """根据精确标题获取论文元数据（用于 fetch_paper_metadata 工具）"""
        papers = self.client.search(title, max_results=5)
        if not papers:
            return None

        title_lower = title.strip().lower()
        best = None
        for p in papers:
            if p.title.strip().lower() == title_lower:
                best = p
                break
        if not best:
            best = papers[0]

        return {
            "title": best.title,
            "authors": best.authors,
            "year": best.year,
            "source": best.source,
            "doi": best.doi,
            "venue": best.venue,
            "url": best.url,
            "abstract": best.abstract,
            "citation_count": best.citation_count,
        }

    def fetch_citation_info_by_title(self, title: str) -> dict | None:
        """根据精确标题获取引用计数（用于 fetch_citation_info 工具）"""
        papers = self.client.search(title, max_results=5)
        if not papers:
            return None

        title_lower = title.strip().lower()
        best = None
        for p in papers:
            if p.title.strip().lower() == title_lower:
                best = p
                break
        if not best:
            best = papers[0]

        return {
            "title": best.title,
            "citation_count": best.citation_count or 0,
            "source": best.source,
        }

    def get_last_scored(self) -> list:
        """返回最近一次 run() 的全部 scored papers（含分数），供 auto-index 过滤使用"""
        return self._last_scored
