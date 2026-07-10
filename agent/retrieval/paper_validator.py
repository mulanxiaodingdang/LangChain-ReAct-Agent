"""论文身份验证：4级置信度 — 身份 + 分数双重判断"""
import re
import unicodedata
from difflib import SequenceMatcher
from enum import Enum
from agent.retrieval.academic_client import AcademicPaper


class ConfidenceLevel(Enum):
    EXACT = "exact"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PaperIdentityValidator:
    HIGH_THRESHOLD = 0.90
    MEDIUM_THRESHOLD = 0.70

    def validate(self, target: str, paper: AcademicPaper, match_score: float,
                 candidate_type: str = "unknown") -> tuple[ConfidenceLevel, str]:
        title = paper.title

        # ── 标识符精确校验 ──
        if candidate_type == "doi" and paper.doi:
            if self._normalize_doi(target) == self._normalize_doi(paper.doi):
                return ConfidenceLevel.EXACT, f"DOI 精确匹配: {paper.doi}"

        if candidate_type == "arxiv_id" and paper.arxiv_id:
            if self._normalize_arxiv_id(target) == self._normalize_arxiv_id(paper.arxiv_id):
                return ConfidenceLevel.EXACT, f"arXiv ID 精确匹配: {paper.arxiv_id}"

        # ── 标题匹配校验 ──
        title_lower = title.lower().strip()

        if candidate_type == "acronym":
            token = target.lower().strip()
            # 标题开头（冒号前部分）
            prefix = title_lower.split(":")[0].strip()
            if prefix == token:
                return ConfidenceLevel.EXACT, f"标题以 acronym 精确开头: {title}"
            # token 后跟分隔符（空格、冒号、连字符）
            if prefix.startswith(token) and (
                len(prefix) == len(token) or prefix[len(token)] in (" ", ":", "-")
            ):
                return ConfidenceLevel.HIGH, f"标题以 acronym 开头: {title}"

        if candidate_type == "full_title":
            norm_target = self._normalize_title(target)
            norm_title = self._normalize_title(title)
            ratio = SequenceMatcher(None, norm_target, norm_title).ratio()
            if ratio >= 0.98:
                return ConfidenceLevel.EXACT, f"标题精确匹配 (sim={ratio:.3f})"
            if ratio >= 0.90:
                return ConfidenceLevel.HIGH, f"标题高相似 (sim={ratio:.3f})"

        # ── 分数兜底（CompositeRanker 输出的 match_score）──
        if match_score >= 0.95:
            return ConfidenceLevel.EXACT, f"分数精确匹配: {title}"
        if match_score >= self.HIGH_THRESHOLD:
            return ConfidenceLevel.HIGH, f"分数高置信度: {title}"
        if match_score >= self.MEDIUM_THRESHOLD:
            return ConfidenceLevel.MEDIUM, f"分数中等置信度: {title}，建议核实论文标题"

        return ConfidenceLevel.LOW, f"低置信度: {title}，检索词与论文标题差异较大"

    # ── 规范化辅助 ──

    @staticmethod
    def _normalize_title(t: str) -> str:
        t = unicodedata.normalize("NFKC", t).casefold()
        return re.sub(r'\s+', ' ', t).strip()

    @staticmethod
    def _normalize_doi(d: str) -> str:
        d = d.strip().lower()
        for prefix in ("https://doi.org/", "http://doi.org/", "doi:", "doi/"):
            if d.startswith(prefix):
                d = d[len(prefix):]
        return d.strip("/")

    @staticmethod
    def _normalize_arxiv_id(aid: str) -> str:
        aid = aid.strip().lower()
        for prefix in ("arxiv:", "arxiv/"):
            if aid.startswith(prefix):
                aid = aid[len(prefix):]
        return aid.strip()


CONFIDENCE_ICONS = {
    ConfidenceLevel.EXACT: "✅",
    ConfidenceLevel.HIGH: "✅",
    ConfidenceLevel.MEDIUM: "⚠",
    ConfidenceLevel.LOW: "❌",
}
