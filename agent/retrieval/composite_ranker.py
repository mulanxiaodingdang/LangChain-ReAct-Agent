"""复合排序器：4种匹配策略取最高分"""
import jieba
from difflib import SequenceMatcher
from agent.retrieval.academic_client import AcademicPaper


class CompositeRanker:
    def __init__(self):
        self.rankers = [
            ExactMatchRanker(),
            SubstringMatchRanker(),
            TokenOverlapRanker(),
            SequenceMatchRanker(),
            ModelNameInTitleRanker(),
        ]

    def rank(self, query: str, papers: list[AcademicPaper]) -> list[tuple[AcademicPaper, float]]:
        scored: list[tuple[AcademicPaper, float]] = []
        query_lower = query.lower().strip()

        for paper in papers:
            best_score = 0.0
            for ranker in self.rankers:
                score = ranker.score(query_lower, paper)
                best_score = max(best_score, score)
            scored.append((paper, best_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


class ExactMatchRanker:
    def score(self, query: str, paper: AcademicPaper) -> float:
        title = paper.title.lower().strip()
        if title == query:
            return 1.0
        # 忽略大小写和空格
        if title.replace(" ", "") == query.replace(" ", ""):
            return 0.95
        return 0.0


class SubstringMatchRanker:
    def score(self, query: str, paper: AcademicPaper) -> float:
        title = paper.title.lower().strip()
        if query in title:
            return 0.7 + 0.3 * (len(query) / max(len(title), 1))
        if title in query:
            return 0.6 + 0.3 * (len(title) / max(len(query), 1))
        return 0.0


class TokenOverlapRanker:
    def score(self, query: str, paper: AcademicPaper) -> float:
        title = paper.title.lower().strip()
        query_tokens = set(jieba.cut(query))
        title_tokens = set(jieba.cut(title))

        if not query_tokens:
            return 0.0

        overlap = query_tokens & title_tokens
        # Jaccard 相似度
        union = query_tokens | title_tokens
        return len(overlap) / len(union) if union else 0.0


class ModelNameInTitleRanker:
    """query 字符串出现在论文标题中 → 固定 0.9 分"""
    def score(self, query: str, paper: AcademicPaper) -> float:
        title = paper.title.lower().strip()
        q = query.lower().strip()
        if q and q in title:
            return 0.90
        return 0.0


class SequenceMatchRanker:
    def score(self, query: str, paper: AcademicPaper) -> float:
        title = paper.title.lower().strip()
        return SequenceMatcher(None, query, title).ratio()
