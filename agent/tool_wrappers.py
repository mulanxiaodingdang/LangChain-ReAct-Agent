"""工具包装器 — 三层装饰：预算控制 + 在线门控 + 日志记录"""
import functools
import time
from typing import Callable
from utils.logger_handler import logger

TOOL_BUDGET_EXHAUSTED = "[TOOL_BUDGET_EXHAUSTED] 工具调用次数已达上限，请基于已有信息直接回答。"
KB_SEARCH_BLOCKED = "[KB_SEARCH_BLOCKED] 已获取在线结果，本地检索被阻止。请基于在线结果回答。"

INVALID_MARKERS = [
    TOOL_BUDGET_EXHAUSTED,
    KB_SEARCH_BLOCKED,
    "[KB_MISS]",
    "[KB_KNOWN_MISSING]",
    "[DUPLICATE]",
    "[PAPER_NOT_FOUND]",
]


def wrap_with_budget(func: Callable, max_calls: int) -> Callable:
    call_counter = [0]

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if call_counter[0] >= max_calls:
            logger.warning(f"[BudgetGuard] {func.__name__} 超配额 (>= {max_calls})")
            return TOOL_BUDGET_EXHAUSTED
        call_counter[0] += 1
        return func(*args, **kwargs)

    wrapper._call_counter = call_counter
    return wrapper


def wrap_with_online_flag(func: Callable, flag_getter: Callable[[], bool]) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if flag_getter():
            logger.info(f"[OnlineFlag] {func.__name__} 已拦截（online_results_obtained=True）")
            return KB_SEARCH_BLOCKED
        return func(*args, **kwargs)

    return wrapper


def wrap_tool_with_logging(func: Callable, tool_name: str) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        arg_str = str(args[0])[:200] if args else str(kwargs)[:200]
        logger.info(f"[Tool] 调用 {tool_name}: {arg_str}")
        start = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            summary = str(result)[:300].replace("\n", " ")
            logger.info(f"[Tool] {tool_name} 完成 ({elapsed:.1f}s) → {summary}")
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"[Tool] {tool_name} 失败 ({elapsed:.1f}s): {e}")
            raise

    return wrapper


def is_invalid_tool_result(content: str) -> bool:
    return any(marker in content for marker in INVALID_MARKERS)
