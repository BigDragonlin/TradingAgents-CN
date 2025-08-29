import builtins
import types


def test_runner_importable():
    import email.analysis.runner as runner
    assert hasattr(runner, "run")


class DummyGraph:
    def __init__(self, debug: bool, config: dict):
        self.debug = debug
        self.config = config

    def propagate(self, ticker: str, date: str):
        return None, {"decision": f"MOCK-{ticker}-{date}"}


def test_runner_run_monkeypatched(monkeypatch):
    import email.analysis.runner as runner

    def fake_graph(*args, **kwargs):
        return DummyGraph(*args, **kwargs)

    monkeypatch.setitem(globals(), "DummyGraph", DummyGraph)

    # 替换 TradingAgentsGraph 为 DummyGraph
    monkeypatch.setattr(
        "email.analysis.runner.TradingAgentsGraph", fake_graph, raising=True
    )

    decision = runner.run()
    assert isinstance(decision, dict)
    assert decision.get("decision", "").startswith("MOCK-")


