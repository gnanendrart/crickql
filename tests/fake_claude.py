"""A stand-in for anthropic.Anthropic that replays scripted tool calls. No network, no cost."""

from types import SimpleNamespace


class FakeClaude:
    def __init__(self, sqls: list[str]):
        self.sqls = list(sqls)
        self.calls: list[dict] = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        sql = self.sqls.pop(0)
        block = SimpleNamespace(type="tool_use", id=f"toolu_{len(self.calls)}", name="run_sql",
                                input={"sql": sql, "reasoning": "scripted"})
        return SimpleNamespace(content=[block], stop_reason="tool_use")
