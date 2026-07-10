"""在线检索管线：query_rewrite → academic_client → composite_ranker → paper_validator"""
from agent.retrieval.query_rewrite import RuleBasedRewriter
from agent.retrieval.academic_client import AcademicDataClient
from agent.retrieval.composite_ranker import CompositeRanker
from agent.retrieval.paper_validator import PaperIdentityValidator, ConfidenceLevel
from utils.logger_handler import logger


class OnlineRetrievalPipeline:
    def __init__(self):
        self.rewriter = RuleBasedRewriter()
        self.client = AcademicDataClient()
        self.ranker = CompositeRanker()
        self.validator = PaperIdentityValidator()

    def run(self, query: str) -> str:
        logger.info(f"[OnlinePipeline]原始query: {query}")

        variants = self.rewriter.rewrite(query)
        logger.info(f"[OnlinePipeline]query变体: {variants}")

        all_papers = self.client.search(query, max_results=20)

        if not all_papers:
            return "未找到相关论文。"

        scored = self.ranker.rank(query, all_papers)

        # 打印 top-3 分数
        for i, (paper, score) in enumerate(scored[:3]):
            logger.info(f"[OnlinePipeline] top{i+1}: score={score:.3f} title={paper.title[:80]}")

        # 只保留 medium 及以上置信度
        valid: list[tuple] = []
        for paper, score in scored:
            level, _ = self.validator.validate(query, paper, score)
            if level in (ConfidenceLevel.EXACT, ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM):
                valid.append((paper, score, level))

        if not valid:
            top_score = f"{scored[0][1]:.2f}" if scored else "N/A"
            return f"未找到高置信度匹配论文（共检索到 {len(scored)} 条结果，最高分 {top_score}，均低于 0.70 阈值）。"

        # 极简输出：每篇一行
        lines = []
        for i, (paper, score, level) in enumerate(valid[:5]):
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
