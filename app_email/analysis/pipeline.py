from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.utils.logging_manager import get_logger
from .buffer import MessageBuffer


logger = get_logger("app_email")


class AnalysisPipeline:
    def __init__(self, selections: Dict):
        self.selections: Dict = selections
        self.config: Dict = {}
        self.graph: Optional[TradingAgentsGraph] = None
        self.results_dir: Optional[Path] = None
        self.report_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None
        self.message_buffer: Optional[MessageBuffer] = None

    # ------------------------
    # Configuration
    # ------------------------
    def configure(self) -> None:
        selections = self.selections
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

        self.config = config

    def init_graph(self) -> None:
        logger.info("正在初始化分析系统...")
        try:
            self.graph = TradingAgentsGraph([analyst.value for analyst in self.selections["analysts"]], config=self.config, debug=True)
            logger.info("分析系统初始化完成")
        except Exception as e:
            logger.error(f"初始化失败 | Initialization failed: {str(e)}")
            raise

    def prepare_outputs(self) -> None:
        project_root = Path(__file__).resolve().parents[2]  # 获取项目根目录
        results_dir = project_root / "results" / self.selections["ticker"] / self.selections["analysis_date"]
        results_dir.mkdir(parents=True, exist_ok=True)
        report_dir = results_dir / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        log_file = results_dir / "message_tool.log"
        log_file.touch(exist_ok=True)

        self.results_dir = results_dir
        self.report_dir = report_dir
        self.log_file = log_file

    # ------------------------
    # Message Buffer setup
    # ------------------------
    def _decorate_message_buffer(self, message_buffer: MessageBuffer) -> None:
        def save_message_decorator(obj, func_name):
            from functools import wraps
            func = getattr(obj, func_name)
            @wraps(func)
            def wrapper(*args, **kwargs):
                func(*args, **kwargs)
                timestamp, message_type, content = obj.messages[-1]
                content = content.replace("\n", " ")
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"{timestamp} [{message_type}] {content}\n")
            return wrapper

        def save_tool_call_decorator(obj, func_name):
            from functools import wraps
            func = getattr(obj, func_name)
            @wraps(func)
            def wrapper(*args, **kwargs):
                func(*args, **kwargs)
                timestamp, tool_name, call_args = obj.tool_calls[-1]
                args_str = ", ".join(f"{k}={v}" for k, v in call_args.items()) if isinstance(call_args, dict) else str(call_args)
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"{timestamp} [Tool Call] {tool_name}({args_str})\n")
            return wrapper

        def save_report_section_decorator(obj, func_name):
            from functools import wraps
            func = getattr(obj, func_name)
            @wraps(func)
            def wrapper(section_name, content):
                func(section_name, content)
                if section_name in obj.report_sections and obj.report_sections[section_name] is not None:
                    content_to_write = obj.report_sections[section_name]
                    if content_to_write:
                        chinese_filenames = {
                            "market_report": "市场分析_01.md",
                            "sentiment_report": "市场情绪分析_02.md",
                            "news_report": "新闻事件分析_03.md",
                            "fundamentals_report": "基本面分析_04.md",
                            "investment_plan": "研究团队决策_05.md",
                            "trader_investment_plan": "交易计划_06.md",
                            "final_trade_decision": "最终投资决策_07.md",
                        }
                        file_name = chinese_filenames.get(section_name, f"{section_name}.md")
                        file_path = self.report_dir / file_name
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(content)
            return wrapper

        # 装饰器将信息添加到log_file中
        message_buffer.add_message = save_message_decorator(message_buffer, "add_message")
        # 装饰器将工具调用信息添加到log_file中
        message_buffer.add_tool_call = save_tool_call_decorator(message_buffer, "add_tool_call")
        # 装饰器将报告段落信息添加到log_file中
        message_buffer.update_report_section = save_report_section_decorator(message_buffer, "update_report_section")

    def setup_message_buffer(self) -> MessageBuffer:
        message_buffer = MessageBuffer()
        # 装饰器将信息添加到log_file中
        self._decorate_message_buffer(message_buffer)

        # 系统信息与初始状态,系统级prompt
        message_buffer.add_message("System", f"Selected ticker: {self.selections['ticker']}")
        message_buffer.add_message("System", f"Analysis date: {self.selections['analysis_date']}")
        message_buffer.add_message("System", f"Selected analysts: {', '.join(analyst.value for analyst in self.selections['analysts'])}")

        for agent in message_buffer.agent_status:
            message_buffer.update_agent_status(agent, "pending")
        for section in message_buffer.report_sections:
            message_buffer.report_sections[section] = None
        message_buffer.current_report = None
        message_buffer.final_report = None

        first_analyst = f"{self.selections['analysts'][0].value.capitalize()} Analyst"
        message_buffer.update_agent_status(first_analyst, "in_progress")

        self.message_buffer = message_buffer
        return message_buffer

    # ------------------------
    # Validation
    # ------------------------
    def validate_data(self) -> bool:
        logger.info("数据验证阶段 | Data Validation Phase")
        logger.info("🔍 验证股票代码并预获取数据...")
        try:
            from tradingagents.utils.stock_validator import prepare_stock_data
            if re.match(r'^\d{6}$', self.selections["ticker"]):
                market_type = "A股"
            elif ".HK" in self.selections["ticker"].upper():
                market_type = "港股"
            else:
                market_type = "美股"

            preparation_result = prepare_stock_data(
                stock_code=self.selections["ticker"],
                market_type=market_type,
                period_days=30,
                analysis_date=self.selections["analysis_date"],
            )
            if not preparation_result.is_valid:
                logger.error(f"❌ 股票数据验证失败: {preparation_result.error_message}")
                logger.warning(f"💡 建议: {preparation_result.suggestion}")
                return False
            logger.info(f"✅ 数据准备完成: {preparation_result.stock_name} ({preparation_result.market_type})")
            logger.info(f"📊 缓存状态: {preparation_result.cache_status}")
            return True
        except Exception as e:
            logger.error(f"❌ 数据预获取过程中发生错误: {str(e)}")
            logger.warning("💡 请检查网络连接或稍后重试")
            return False
        
    
    def extract_content_string(content):
        """
        从各种消息格式中提取字符串内容
        Extract string content from various message formats
        
        Args:
            content: 消息内容，可能是字符串、列表或其他格式
        
        Returns:
            str: 提取的字符串内容
        """
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            # Handle Anthropic's list format
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    item_type = item.get('type')  # 缓存type值
                    if item_type == 'text':
                        text_parts.append(item.get('text', ''))
                    elif item_type == 'tool_use':
                        tool_name = item.get('name', 'unknown')  # 缓存name值
                        text_parts.append(f"[Tool: {tool_name}]")
                else:
                    text_parts.append(str(item))
            return ' '.join(text_parts)
        else:
            return str(content)

    # ------------------------
    # Streaming analysis
    # ------------------------
    def run_stream(self) -> List[Dict]:
        assert self.graph is not None
        assert self.message_buffer is not None

        logger.info("数据获取阶段 | Data Collection Phase")
        logger.info("正在获取股票基本信息...")
        init_agent_state = self.graph.propagator.create_initial_state(self.selections["ticker"], self.selections["analysis_date"])
        args = self.graph.propagator.get_graph_args()
        logger.info("数据获取准备完成")

        logger.info("智能分析阶段 | AI Analysis Phase (预计耗时约10分钟)")
        logger.info("启动分析师团队...")
        logger.info("💡 提示：智能分析包含多个团队协作，请耐心等待约10分钟")

        trace: List[Dict] = []
        completed_analysts = set()
        graph = self.graph
        message_buffer = self.message_buffer

        for chunk in graph.graph.stream(init_agent_state, **args):
            if len(chunk["messages"]) > 0:
                # 获取最后一条消息
                last_message = chunk["messages"][-1]
                
                # 提取消息内容和类型
                if hasattr(last_message, "content"):

                    content = getattr(last_message, "content", str(last_message))
                    # content = self.extract_content_string(last_message.content)  # Use the helper function
                    msg_type = "Reasoning"
                else:
                    content = str(last_message)
                    msg_type = "System"

                # 添加消息到缓冲区
                message_buffer.add_message(msg_type, content)

                # 如果有工具调用，添加到缓冲区
                if hasattr(last_message, "tool_calls"):
                    for tool_call in last_message.tool_calls:
                        if isinstance(tool_call, dict):
                            message_buffer.add_tool_call(tool_call["name"], tool_call["args"])
                        else:
                            message_buffer.add_tool_call(tool_call.name, tool_call.args)
                
                # -------------------市场分析
                if "market_report" in chunk and chunk["market_report"]:
                    # 只在第一次完成时显示提示
                    if "market_report" not in completed_analysts:
                        logger.info("📈 市场分析完成")
                        completed_analysts.add("market_report")
                        # 调试信息（写入日志文件）
                        logger.info(f"首次显示市场分析完成提示，已完成分析师: {completed_analysts}")
                    else:
                        # 调试信息（写入日志文件）
                        logger.debug(f"跳过重复的市场分析完成提示，已完成分析师: {completed_analysts}")

                    message_buffer.update_report_section(
                        "market_report", chunk["market_report"]
                    )
                    message_buffer.update_agent_status("Market Analyst", "completed")
                    # Set next analyst to in_progress
                    if "social" in self.selections["analysts"]:
                        message_buffer.update_agent_status(
                            "Social Analyst", "in_progress"
                        )
                    
                # -------------------情感分析
                if "sentiment_report" in chunk and chunk["sentiment_report"]:
                    # 只在第一次完成时显示提示
                    if "sentiment_report" not in completed_analysts:
                        logger.info("💭 情感分析完成")
                        completed_analysts.add("sentiment_report")
                        # 调试信息（写入日志文件）
                        logger.info(f"首次显示情感分析完成提示，已完成分析师: {completed_analysts}")
                    else:
                        # 调试信息（写入日志文件）
                        logger.debug(f"跳过重复的情感分析完成提示，已完成分析师: {completed_analysts}")

                    message_buffer.update_report_section(
                        "sentiment_report", chunk["sentiment_report"]
                    )
                    message_buffer.update_agent_status("Social Analyst", "completed")
                    # Set next analyst to in_progress
                    if "news" in self.selections["analysts"]:
                        message_buffer.update_agent_status(
                            "News Analyst", "in_progress"
                        )

                # -------------------新闻分析
                if "news_report" in chunk and chunk["news_report"]:
                    # 只在第一次完成时显示提示
                    if "news_report" not in completed_analysts:
                        logger.info("📰 新闻分析完成")
                        completed_analysts.add("news_report")
                        # 调试信息（写入日志文件）
                        logger.info(f"首次显示新闻分析完成提示，已完成分析师: {completed_analysts}")
                    else:
                        # 调试信息（写入日志文件）
                        logger.debug(f"跳过重复的新闻分析完成提示，已完成分析师: {completed_analysts}")

                    message_buffer.update_report_section(
                        "news_report", chunk["news_report"]
                    )
                    message_buffer.update_agent_status("News Analyst", "completed")
                    # Set next analyst to in_progress
                    if "fundamentals" in self.selections["analysts"]:
                        message_buffer.update_agent_status(
                            "Fundamentals Analyst", "in_progress"
                        )

                # -------------------基本面分析
                if "fundamentals_report" in chunk and chunk["fundamentals_report"]:
                    # 只在第一次完成时显示提示
                    if "fundamentals_report" not in completed_analysts:
                        logger.info("📊 基本面分析完成")
                        completed_analysts.add("fundamentals_report")
                        # 调试信息（写入日志文件）
                        logger.info(f"首次显示基本面分析完成提示，已完成分析师: {completed_analysts}")
                    else:
                        # 调试信息（写入日志文件）
                        logger.debug(f"跳过重复的基本面分析完成提示，已完成分析师: {completed_analysts}")

                    message_buffer.update_report_section(
                        "fundamentals_report", chunk["fundamentals_report"]
                    )
                    message_buffer.update_agent_status(
                        "Fundamentals Analyst", "completed"
                    )
                    # Set all research team members to in_progress
                    for agent in ["Bull Researcher", "Bear Researcher", "Research Manager", "Trader"]:
                        message_buffer.update_agent_status(agent, "in_progress")

                
                # -------------------研究团队决策
                if (
                    "investment_debate_state" in chunk
                    and chunk["investment_debate_state"]
                ):
                    debate_state = chunk["investment_debate_state"]

                    # -------------------多头研究员分析
                    if "bull_history" in debate_state and debate_state["bull_history"]:
                        # 显示研究团队开始工作
                        if "research_team_started" not in completed_analysts:
                            logger.info("🔬 研究团队开始深度分析...")
                            completed_analysts.add("research_team_started")

                        # 更新研究团队成员状态为in_progress
                        for agent in ["Bull Researcher", "Bear Researcher", "Research Manager", "Trader"]:
                            message_buffer.update_agent_status(agent, "in_progress")
                        # 提取最新多头研究员响应
                        bull_responses = debate_state["bull_history"].split("\n")
                        latest_bull = bull_responses[-1] if bull_responses else ""
                        if latest_bull:
                            message_buffer.add_message("Reasoning", latest_bull)
                            # 更新带有多头研究员分析的报告
                            message_buffer.update_report_section(
                                "investment_plan",
                                f"### Bull Researcher Analysis\n{latest_bull}",
                            )

                    # -------------------空头研究员分析
                    if "bear_history" in debate_state and debate_state["bear_history"]:
                        # 更新研究团队成员状态为in_progress
                        for agent in ["Bull Researcher", "Bear Researcher", "Research Manager", "Trader"]:
                            message_buffer.update_agent_status(agent, "in_progress")
                        # 提取最新空头研究员响应
                        bear_responses = debate_state["bear_history"].split("\n")
                        latest_bear = bear_responses[-1] if bear_responses else ""
                        if latest_bear:
                            message_buffer.add_message("Reasoning", latest_bear)
                            # Update research report with bear's latest analysis
                            message_buffer.update_report_section(
                                "investment_plan",
                                f"{message_buffer.report_sections['investment_plan']}\n\n### Bear Researcher Analysis\n{latest_bear}",
                            )

                    # Update Research Manager status and final decision
                    if (
                        "judge_decision" in debate_state
                        and debate_state["judge_decision"]
                    ):
                        # 显示研究团队完成
                        if "research_team" not in completed_analysts:
                            logger.info("🔬 研究团队分析完成")
                            completed_analysts.add("research_team")

                        # 更新研究团队成员状态为in_progress直到最终决策
                        for agent in ["Bull Researcher", "Bear Researcher", "Research Manager", "Trader"]:
                            message_buffer.update_agent_status(agent, "in_progress")
                        message_buffer.add_message(
                            "Reasoning",
                            f"Research Manager: {debate_state['judge_decision']}",
                        )
                        # 更新带有多头研究员分析的报告
                        message_buffer.update_report_section(
                            "investment_plan",
                            f"{message_buffer.report_sections['investment_plan']}\n\n### Research Manager Decision\n{debate_state['judge_decision']}",
                        )
                        # 更新研究团队成员状态为completed
                        for agent in ["Bull Researcher", "Bear Researcher", "Research Manager", "Trader"]:
                            message_buffer.update_agent_status(agent, "completed")
                        # 更新风险分析师状态为in_progress
                        message_buffer.update_agent_status(
                            "Risky Analyst", "in_progress"
                        )
                
                # -------------------交易团队
                if (
                    "trader_investment_plan" in chunk
                    and chunk["trader_investment_plan"]
                ):
                    # 显示交易团队开始工作
                    if "trading_team_started" not in completed_analysts:
                        logger.info("💼 交易团队制定投资计划...")
                        completed_analysts.add("trading_team_started")

                    # 显示交易团队完成
                    if "trading_team" not in completed_analysts:
                        logger.info("💼 交易团队计划完成")
                        completed_analysts.add("trading_team")

                    message_buffer.update_report_section(
                        "trader_investment_plan", chunk["trader_investment_plan"]
                    )
                    # Set first risk analyst to in_progress
                    message_buffer.update_agent_status("Risky Analyst", "in_progress")

                # -------------------风险管理团队
                if "risk_debate_state" in chunk and chunk["risk_debate_state"]:
                    risk_state = chunk["risk_debate_state"]

                    # -------------------风险分析师分析
                    if (
                        "current_risky_response" in risk_state
                        and risk_state["current_risky_response"]
                    ):
                        # 显示风险管理团队开始工作
                        if "risk_team_started" not in completed_analysts:
                            logger.info("⚖️ 风险管理团队评估投资风险...")
                            completed_analysts.add("risk_team_started")

                        message_buffer.update_agent_status(
                            "Risky Analyst", "in_progress"
                        )
                        message_buffer.add_message(
                            "Reasoning",
                            f"Risky Analyst: {risk_state['current_risky_response']}",
                        )
                        # Update risk report with risky analyst's latest analysis only
                        message_buffer.update_report_section(
                            "final_trade_decision",
                            f"### Risky Analyst Analysis\n{risk_state['current_risky_response']}",
                        )

                    # -------------------保守分析师分析
                    if (
                        "current_safe_response" in risk_state
                        and risk_state["current_safe_response"]
                    ):
                        message_buffer.update_agent_status(
                            "Safe Analyst", "in_progress"
                        )
                        message_buffer.add_message(
                            "Reasoning",
                            f"Safe Analyst: {risk_state['current_safe_response']}",
                        )
                        # Update risk report with safe analyst's latest analysis only
                        message_buffer.update_report_section(
                            "final_trade_decision",
                            f"### Safe Analyst Analysis\n{risk_state['current_safe_response']}",
                        )

                    # -------------------中性分析师分析
                    if (
                        "current_neutral_response" in risk_state
                        and risk_state["current_neutral_response"]
                    ):
                        message_buffer.update_agent_status(
                            "Neutral Analyst", "in_progress"
                        )
                        message_buffer.add_message(
                            "Reasoning",
                            f"Neutral Analyst: {risk_state['current_neutral_response']}",
                        )
                        # Update risk report with neutral analyst's latest analysis only
                        message_buffer.update_report_section(
                            "final_trade_decision",
                            f"### Neutral Analyst Analysis\n{risk_state['current_neutral_response']}",
                        )

                    # -------------------投资经理分析
                    if "judge_decision" in risk_state and risk_state["judge_decision"]:
                        # 显示风险管理团队完成
                        if "risk_management" not in completed_analysts:
                            logger.info("⚖️ 风险管理团队分析完成")
                            completed_analysts.add("risk_management")

                        message_buffer.update_agent_status(
                            "Portfolio Manager", "in_progress"
                        )
                        message_buffer.add_message(
                            "Reasoning",
                            f"Portfolio Manager: {risk_state['judge_decision']}",
                        )
                        # 更新带有多头研究员分析的报告
                        message_buffer.update_report_section(
                            "final_trade_decision",
                            f"### Portfolio Manager Decision\n{risk_state['judge_decision']}",
                        )
                        # 更新风险分析师状态为completed
                        message_buffer.update_agent_status("Risky Analyst", "completed")
                        message_buffer.update_agent_status("Safe Analyst", "completed")
                        message_buffer.update_agent_status(
                            "Neutral Analyst", "completed"
                        )
                        message_buffer.update_agent_status(
                            "Portfolio Manager", "completed"
                        )
            trace.append(chunk)
        return trace

    # ------------------------
    # Post-processing
    # ------------------------
    def process_decision(self, trace: List[Dict]) -> None:
        assert self.graph is not None
        assert self.message_buffer is not None
        logger.info("投资决策生成 | Investment Decision Generation")
        logger.info("正在处理投资信号...")
        final_state = trace[-1]
        _decision = self.graph.process_signal(final_state["final_trade_decision"], self.selections['ticker'])

        logger.info("🤖 投资信号处理完成")
        
        # 更新所有分析师状态为completed
        for agent in self.message_buffer.agent_status:
            self.message_buffer.update_agent_status(agent, "completed")

        self.message_buffer.add_message("Analysis", f"Completed analysis for {self.selections['analysis_date']}")

        # 更新最后报告部分
        for section in list(self.message_buffer.report_sections.keys()):
            if section in final_state:
                self.message_buffer.update_report_section(section, final_state[section])

    def generate_report(self) -> None:
        logger.info("分析报告生成 | Analysis Report Generation")
        logger.info("正在生成最终报告...")
        logger.info("📋 分析报告生成完成")
        logger.info(f"🎉 {self.selections['ticker']} 股票分析全部完成！")


