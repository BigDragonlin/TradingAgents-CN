from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('default')


def run() -> str:
    """运行示例分析并返回最终决策。"""
    # Create a custom config（保持与根 main.py 一致的默认行为）
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = "google"
    config["backend_url"] = "https://generativelanguage.googleapis.com/v1"
    config["deep_think_llm"] = "gemini-2.0-flash"
    config["quick_think_llm"] = "gemini-2.0-flash"
    config["max_debate_rounds"] = 1
    config["online_tools"] = True

    # Initialize with custom config
    ta = TradingAgentsGraph(debug=True, config=config)

    # forward propagate（保持原始样例参数）
    _, decision = ta.propagate("NVDA", "2024-05-10")
    print(decision)
    return decision


def main():
    run()


if __name__ == "__main__":
    main()


