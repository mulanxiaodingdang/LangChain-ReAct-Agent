"""意图分类器 — LLM 分类 + 关键词兜底，将 query 分为 qa / compare / review"""
from enum import Enum
from model.factory import chat_model
from utils.logger_handler import logger


class Intent(str, Enum):
    QA = "qa"
    COMPARE = "compare"
    REVIEW = "review"


COMPARE_KEYWORDS = [
    "vs", "versus", "compare", "comparison", "difference", "diff",
    "对比", "比较", "区别", "异同", "优劣", "哪个更好", "有什么不同",
    "区别是什么", "优缺点", "对比分析",
]

REVIEW_KEYWORDS = [
    "review", "survey", "overview", "literature", "state of the art",
    "综述", "概述", "概览", "发展脉络", "研究现状", "研究进展",
    "总结", "归纳", "梳理", "全面了解", "领域发展", "主流方法",
    "systematic review", "comprehensive", "taxonomy",
]


class IntentRouter:
    def __init__(self):
        self._classify_prompt = (
            "将以下用户问题分类为以下三类之一。只回复一个单词：qa、compare 或 review。\n"
            "- qa: 关于特定论文/方法/概念的具体问题\n"
            "- compare: 比较多个方法/模型/论文\n"
            "- review: 全面了解某个研究领域的发展\n"
            "问题：{query}\n分类："
        )

    def classify(self, query: str) -> Intent:
        llm_result = self._llm_classify(query)
        if llm_result:
            return llm_result
        return self._keyword_fallback(query)

    def _llm_classify(self, query: str) -> Intent | None:
        try:
            response = chat_model.invoke(
                self._classify_prompt.format(query=query),
                temperature=0,
                max_tokens=5,
            )
            text = response.content.strip().lower()
            for intent in Intent:
                if intent.value in text:
                    logger.info(f"[IntentRouter] LLM 分类: {intent.value}")
                    return intent
            return None
        except Exception as e:
            logger.warning(f"[IntentRouter] LLM 分类失败: {e}")
            return None

    def _keyword_fallback(self, query: str) -> Intent:
        query_lower = query.lower()
        compare_score = sum(1 for kw in COMPARE_KEYWORDS if kw in query_lower)
        review_score = sum(1 for kw in REVIEW_KEYWORDS if kw in query_lower)

        if compare_score > review_score:
            logger.info(f"[IntentRouter] 关键词兜底: compare (C={compare_score} R={review_score})")
            return Intent.COMPARE
        elif review_score > compare_score:
            logger.info(f"[IntentRouter] 关键词兜底: review (C={compare_score} R={review_score})")
            return Intent.REVIEW
        elif compare_score > 0 and compare_score == review_score:
            logger.info(f"[IntentRouter] 关键词兜底: compare (平局偏好)")
            return Intent.COMPARE
        else:
            logger.info(f"[IntentRouter] 关键词兜底: qa (默认)")
            return Intent.QA
