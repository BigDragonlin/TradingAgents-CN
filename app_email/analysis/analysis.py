import os
import re
from pathlib import Path
from typing import Dict

import typer
from rich.console import Console
from rich.live import Live

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.utils.logging_manager import get_logger

from .buffer import MessageBuffer
from .constants import DEFAULT_REFRESH_RATE
from .layout import create_layout, update_display
from .keys import check_api_keys
from .report import display_complete_report
from .selections import get_user_selections
from .testConfig import CONFIG
from .ui import CLIUserInterface


logger = get_logger("cli")


def run_analysis():
    import time
    start_time = time.time()

    ui = CLIUserInterface()
    console = Console()

    # selections = get_user_selections(console)
    selections = CONFIG
    if not check_api_keys(selections["llm_provider"]):
        ui.show_error("分析终止 | Analysis terminated")
        return

    ui.show_step_header(1, "准备分析环境 | Preparing Analysis Environment")
    ui.show_progress(f"正在分析股票: {selections['ticker']}")
    ui.show_progress(f"分析日期: {selections['analysis_date']}")
    ui.show_progress(f"选择的分析师: {', '.join(analyst.value for analyst in selections['analysts'])}")

    config = DEFAULT_CONFIG.copy()
    config["max_debate_rounds"] = selections["research_depth"]
    config["max_risk_discuss_rounds"] = selections["research_depth"]
    config["quick_think_llm"] = selections["shallow_thinker"]
    config["deep_think_llm"] = selections["deep_thinker"]
    config["backend_url"] = selections["backend_url"]

    selected_llm_provider_name = selections["llm_provider"].lower()
    if "阿里百炼" in selections["llm_provider"] or "dashscope" in selected_llm_provider_name:
        config["llm_provider"] = "dashscope"
    elif "deepseek" in selected_llm_provider_name or "DeepSeek" in selections["llm_provider"]:
        config["llm_provider"] = "deepseek"
    elif "openai" in selected_llm_provider_name and "自定义" not in selections["llm_provider"]:
        config["llm_provider"] = "openai"
    elif "自定义openai端点" in selected_llm_provider_name or "自定义" in selections["llm_provider"]:
        config["llm_provider"] = "custom_openai"
        custom_url = os.getenv('CUSTOM_OPENAI_BASE_URL', selections["backend_url"])
        config["custom_openai_base_url"] = custom_url
        config["backend_url"] = custom_url
    elif "anthropic" in selected_llm_provider_name:
        config["llm_provider"] = "anthropic"
    elif "google" in selected_llm_provider_name:
        config["llm_provider"] = "google"
    else:
        config["llm_provider"] = selected_llm_provider_name

    ui.show_progress("正在初始化分析系统...")
    try:
        graph = TradingAgentsGraph([analyst.value for analyst in selections["analysts"]], config=config, debug=True)
        ui.show_success("分析系统初始化完成")
    except Exception as e:
        ui.show_error(f"初始化失败 | Initialization failed: {str(e)}")
        return

    results_dir = Path(config["results_dir"]) / selections["ticker"] / selections["analysis_date"]
    results_dir.mkdir(parents=True, exist_ok=True)
    report_dir = results_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    log_file = results_dir / "message_tool.log"
    log_file.touch(exist_ok=True)

    message_buffer = MessageBuffer()

    def save_message_decorator(obj, func_name):
        from functools import wraps
        func = getattr(obj, func_name)
        @wraps(func)
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            timestamp, message_type, content = obj.messages[-1]
            content = content.replace("\n", " ")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} [{message_type}] {content}\n")
        return wrapper

    def save_tool_call_decorator(obj, func_name):
        from functools import wraps
        func = getattr(obj, func_name)
        @wraps(func)
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            timestamp, tool_name, args = obj.tool_calls[-1]
            args_str = ", ".join(f"{k}={v}" for k, v in args.items()) if isinstance(args, dict) else str(args)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} [Tool Call] {tool_name}({args_str})\n")
        return wrapper

    def save_report_section_decorator(obj, func_name):
        from functools import wraps
        func = getattr(obj, func_name)
        @wraps(func)
        def wrapper(section_name, content):
            func(section_name, content)
            if section_name in obj.report_sections and obj.report_sections[section_name] is not None:
                content = obj.report_sections[section_name]
                if content:
                    file_name = f"{section_name}.md"
                    with open(report_dir / file_name, "w", encoding="utf-8") as f:
                        f.write(content)
        return wrapper

    message_buffer.add_message = save_message_decorator(message_buffer, "add_message")
    message_buffer.add_tool_call = save_tool_call_decorator(message_buffer, "add_tool_call")
    message_buffer.update_report_section = save_report_section_decorator(message_buffer, "update_report_section")

    layout = create_layout()


    from rich.live import Live
    with Live(layout, refresh_per_second=DEFAULT_REFRESH_RATE) as live:
        update_display(layout, message_buffer)
        message_buffer.add_message("System", f"Selected ticker: {selections['ticker']}")
        message_buffer.add_message("System", f"Analysis date: {selections['analysis_date']}")
        message_buffer.add_message("System", f"Selected analysts: {', '.join(analyst.value for analyst in selections['analysts'])}")
        update_display(layout, message_buffer)

        for agent in message_buffer.agent_status:
            message_buffer.update_agent_status(agent, "pending")
        for section in message_buffer.report_sections:
            message_buffer.report_sections[section] = None
        message_buffer.current_report = None
        message_buffer.final_report = None

        first_analyst = f"{selections['analysts'][0].value.capitalize()} Analyst"
        message_buffer.update_agent_status(first_analyst, "in_progress")
        update_display(layout, message_buffer)

        spinner_text = f"Analyzing {selections['ticker']} on {selections['analysis_date']}..."
        update_display(layout, message_buffer, spinner_text)

        ui.show_step_header(2, "数据验证阶段 | Data Validation Phase")
        ui.show_progress("🔍 验证股票代码并预获取数据...")

        try:
            from tradingagents.utils.stock_validator import prepare_stock_data
            if re.match(r'^\d{6}$', selections["ticker"]):
                market_type = "A股"
            elif ".HK" in selections["ticker"].upper():
                market_type = "港股"
            else:
                market_type = "美股"

            preparation_result = prepare_stock_data(
                stock_code=selections["ticker"],
                market_type=market_type,
                period_days=30,
                analysis_date=selections["analysis_date"],
            )
            if not preparation_result.is_valid:
                ui.show_error(f"❌ 股票数据验证失败: {preparation_result.error_message}")
                ui.show_warning(f"💡 建议: {preparation_result.suggestion}")
                return
            ui.show_success(f"✅ 数据准备完成: {preparation_result.stock_name} ({preparation_result.market_type})")
            ui.show_user_message(f"📊 缓存状态: {preparation_result.cache_status}", "dim")
        except Exception as e:
            ui.show_error(f"❌ 数据预获取过程中发生错误: {str(e)}")
            ui.show_warning("💡 请检查网络连接或稍后重试")
            return

        ui.show_step_header(3, "数据获取阶段 | Data Collection Phase")
        ui.show_progress("正在获取股票基本信息...")
        init_agent_state = graph.propagator.create_initial_state(selections["ticker"], selections["analysis_date"])
        args = graph.propagator.get_graph_args()
        ui.show_success("数据获取准备完成")

        ui.show_step_header(4, "智能分析阶段 | AI Analysis Phase (预计耗时约10分钟)")
        ui.show_progress("启动分析师团队...")
        ui.show_user_message("💡 提示：智能分析包含多个团队协作，请耐心等待约10分钟", "dim")

        trace = []
        completed_analysts = set()
        for chunk in graph.graph.stream(init_agent_state, **args):
            if len(chunk["messages"]) > 0:
                last_message = chunk["messages"][-1]
                content = getattr(last_message, "content", str(last_message))
                if not isinstance(content, str):
                    content = str(content)
                msg_type = "Reasoning" if hasattr(last_message, "content") else "System"
                message_buffer.add_message(msg_type, content)
                if hasattr(last_message, "tool_calls"):
                    for tool_call in last_message.tool_calls:
                        if isinstance(tool_call, dict):
                            message_buffer.add_tool_call(tool_call.get("name", "unknown"), tool_call.get("args", {}))
                        else:
                            message_buffer.add_tool_call(getattr(tool_call, "name", "unknown"), getattr(tool_call, "args", {}))

                if chunk.get("market_report"):
                    if "market_report" not in completed_analysts:
                        ui.show_success("📈 市场分析完成")
                        completed_analysts.add("market_report")
                    message_buffer.update_report_section("market_report", chunk["market_report"])
                    message_buffer.update_agent_status("Market Analyst", "completed")
                    message_buffer.update_agent_status("Social Analyst", "in_progress")

                if chunk.get("sentiment_report"):
                    if "sentiment_report" not in completed_analysts:
                        ui.show_success("💭 情感分析完成")
                        completed_analysts.add("sentiment_report")
                    message_buffer.update_report_section("sentiment_report", chunk["sentiment_report"])
                    message_buffer.update_agent_status("Social Analyst", "completed")
                    message_buffer.update_agent_status("News Analyst", "in_progress")

                if chunk.get("news_report"):
                    if "news_report" not in completed_analysts:
                        ui.show_success("📰 新闻分析完成")
                        completed_analysts.add("news_report")
                    message_buffer.update_report_section("news_report", chunk["news_report"])
                    message_buffer.update_agent_status("News Analyst", "completed")
                    message_buffer.update_agent_status("Fundamentals Analyst", "in_progress")

                if chunk.get("fundamentals_report"):
                    if "fundamentals_report" not in completed_analysts:
                        ui.show_success("📊 基本面分析完成")
                        completed_analysts.add("fundamentals_report")
                    message_buffer.update_report_section("fundamentals_report", chunk["fundamentals_report"])
                    message_buffer.update_agent_status("Fundamentals Analyst", "completed")
                    for agent in ["Bull Researcher", "Bear Researcher", "Research Manager", "Trader"]:
                        message_buffer.update_agent_status(agent, "in_progress")

                if chunk.get("investment_debate_state"):
                    debate_state = chunk["investment_debate_state"]
                    if debate_state.get("bull_history"):
                        bull_lines = debate_state["bull_history"].split("\n")
                        latest_bull = bull_lines[-1] if bull_lines else ""
                        if latest_bull:
                            message_buffer.add_message("Reasoning", latest_bull)
                            message_buffer.update_report_section("investment_plan", f"### Bull Researcher Analysis\n{latest_bull}")
                    if debate_state.get("bear_history"):
                        bear_lines = debate_state["bear_history"].split("\n")
                        latest_bear = bear_lines[-1] if bear_lines else ""
                        if latest_bear:
                            message_buffer.add_message("Reasoning", latest_bear)
                            message_buffer.update_report_section("investment_plan", f"{message_buffer.report_sections['investment_plan']}\n\n### Bear Researcher Analysis\n{latest_bear}")
                    if debate_state.get("judge_decision"):
                        message_buffer.add_message("Reasoning", f"Research Manager: {debate_state['judge_decision']}")
                        message_buffer.update_report_section("investment_plan", f"{message_buffer.report_sections['investment_plan']}\n\n### Research Manager Decision\n{debate_state['judge_decision']}")
                        for agent in ["Bull Researcher", "Bear Researcher", "Research Manager"]:
                            message_buffer.update_agent_status(agent, "completed")
                        message_buffer.update_agent_status("Risky Analyst", "in_progress")

                if chunk.get("trader_investment_plan"):
                    if "trading_team" not in completed_analysts:
                        message_buffer.update_report_section("trader_investment_plan", chunk["trader_investment_plan"])
                        message_buffer.update_agent_status("Risky Analyst", "in_progress")

                if chunk.get("risk_debate_state"):
                    risk_state = chunk["risk_debate_state"]
                    if risk_state.get("current_risky_response"):
                        message_buffer.update_agent_status("Risky Analyst", "in_progress")
                        message_buffer.add_message("Reasoning", f"Risky Analyst: {risk_state['current_risky_response']}")
                        message_buffer.update_report_section("final_trade_decision", f"### Risky Analyst Analysis\n{risk_state['current_risky_response']}")
                    if risk_state.get("current_safe_response"):
                        message_buffer.update_agent_status("Safe Analyst", "in_progress")
                        message_buffer.add_message("Reasoning", f"Safe Analyst: {risk_state['current_safe_response']}")
                        message_buffer.update_report_section("final_trade_decision", f"### Safe Analyst Analysis\n{risk_state['current_safe_response']}")
                    if risk_state.get("current_neutral_response"):
                        message_buffer.update_agent_status("Neutral Analyst", "in_progress")
                        message_buffer.add_message("Reasoning", f"Neutral Analyst: {risk_state['current_neutral_response']}")
                        message_buffer.update_report_section("final_trade_decision", f"### Neutral Analyst Analysis\n{risk_state['current_neutral_response']}")
                    if risk_state.get("judge_decision"):
                        message_buffer.update_agent_status("Portfolio Manager", "in_progress")
                        message_buffer.add_message("Reasoning", f"Portfolio Manager: {risk_state['judge_decision']}")
                        message_buffer.update_report_section("final_trade_decision", f"### Portfolio Manager Decision\n{risk_state['judge_decision']}")
                        for agent in ["Risky Analyst", "Safe Analyst", "Neutral Analyst", "Portfolio Manager"]:
                            message_buffer.update_agent_status(agent, "completed")

                update_display(layout, message_buffer)
            trace.append(chunk)

        ui.show_step_header(5, "投资决策生成 | Investment Decision Generation")
        ui.show_progress("正在处理投资信号...")
        final_state = trace[-1]
        decision = graph.process_signal(final_state["final_trade_decision"], selections['ticker'])
        ui.show_success("🤖 投资信号处理完成")
        for agent in message_buffer.agent_status:
            message_buffer.update_agent_status(agent, "completed")
        message_buffer.add_message("Analysis", f"Completed analysis for {selections['analysis_date']}")
        for section in list(message_buffer.report_sections.keys()):
            if section in final_state:
                message_buffer.update_report_section(section, final_state[section])
        ui.show_step_header(6, "分析报告生成 | Analysis Report Generation")
        ui.show_progress("正在生成最终报告...")
        display_complete_report(console, final_state)
        ui.show_success("📋 分析报告生成完成")
        ui.show_success(f"🎉 {selections['ticker']} 股票分析全部完成！")
        total_time = time.time() - start_time
        ui.show_user_message(f"⏱️ 总分析时间: {total_time:.1f}秒", "dim")
        update_display(layout, message_buffer)


