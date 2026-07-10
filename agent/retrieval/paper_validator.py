"""论文身份验证：4级置信度"""
from enum import Enum
from agent.retrieval.academic_client import AcademicPaper


class ConfidenceLevel(Enum):
    EXACT = "exact"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PaperIdentityValidator:
    HIGH_THRESHOLD = 0.9
    MEDIUM_THRESHOLD = 0.7

    def validate(self, query: str, paper: AcademicPaper, match_score: float) -> tuple[ConfidenceLevel, str]:
        title = paper.title

        # 完全匹配
        if match_score >= 0.95:
            return ConfidenceLevel.EXACT, f"精确匹配: {title}"

        if match_score >= self.HIGH_THRESHOLD:
            return ConfidenceLevel.HIGH, f"高置信度匹配: {title}"

        if match_score >= self.MEDIUM_THRESHOLD:
            return ConfidenceLevel.MEDIUM, f"中等置信度匹配: {title}，建议核实论文标题"

        return ConfidenceLevel.LOW, f"低置信度匹配: {title}，检索词与论文标题差异较大，请勿直接使用该论文摘要内容"


CONFIDENCE_ICONS = {
    ConfidenceLevel.EXACT: "✅",
    ConfidenceLevel.HIGH: "✅",
    ConfidenceLevel.MEDIUM: "⚠",
    ConfidenceLevel.LOW: "❌",
}
