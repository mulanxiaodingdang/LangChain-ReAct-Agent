"""执行策略 — 工具配额 + 空轮次监控 + 强制终止"""
from dataclasses import dataclass
from langchain_core.messages import SystemMessage


STOP_MESSAGE = "已收集足够信息，请直接回答用户问题。不要调用更多工具。"


@dataclass
class AgentExecutionPolicy:
    max_tool_calls: int = 15
    max_empty_rounds: int = 2
    round_counter: int = 0
    effective_rounds: int = 0
    empty_rounds_consecutive: int = 0
    stopped: bool = False
    stop_yielded: bool = False

    def reset(self):
        self.round_counter = 0
        self.effective_rounds = 0
        self.empty_rounds_consecutive = 0
        self.stopped = False
        self.stop_yielded = False

    def mark_round_effective(self):
        self.effective_rounds += 1
        self.round_counter += 1
        self.empty_rounds_consecutive = 0

    def mark_round_empty(self):
        self.round_counter += 1
        self.empty_rounds_consecutive += 1
        if self.empty_rounds_consecutive >= self.max_empty_rounds:
            self.stopped = True

    def should_stop(self) -> bool:
        return self.stopped

    def inject_stop_message(self, messages: list) -> list:
        if self.stop_yielded:
            return messages
        self.stop_yielded = True
        return list(messages) + [SystemMessage(content=STOP_MESSAGE)]
