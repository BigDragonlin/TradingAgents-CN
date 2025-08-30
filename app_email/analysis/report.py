from rich.columns import Columns
from rich.panel import Panel
from rich.markdown import Markdown


def display_complete_report(console, final_state):
    # I. Analyst Team Reports
    analyst_reports = []
    if final_state.get("market_report"):
        analyst_reports.append(Panel(Markdown(final_state["market_report"]), title="Market Analyst", border_style="blue", padding=(1, 2)))
    if final_state.get("sentiment_report"):
        analyst_reports.append(Panel(Markdown(final_state["sentiment_report"]), title="Social Analyst", border_style="blue", padding=(1, 2)))
    if final_state.get("news_report"):
        analyst_reports.append(Panel(Markdown(final_state["news_report"]), title="News Analyst", border_style="blue", padding=(1, 2)))
    if final_state.get("fundamentals_report"):
        analyst_reports.append(Panel(Markdown(final_state["fundamentals_report"]), title="Fundamentals Analyst", border_style="blue", padding=(1, 2)))
    if analyst_reports:
        console.print(Panel(Columns(analyst_reports, equal=True, expand=True), title="I. Analyst Team Reports", border_style="cyan", padding=(1, 2)))

    # II. Research Team Reports
    if final_state.get("investment_debate_state"):
        research_reports = []
        debate_state = final_state["investment_debate_state"]
        if debate_state.get("bull_history"):
            research_reports.append(Panel(Markdown(debate_state["bull_history"]), title="Bull Researcher", border_style="blue", padding=(1, 2)))
        if debate_state.get("bear_history"):
            research_reports.append(Panel(Markdown(debate_state["bear_history"]), title="Bear Researcher", border_style="blue", padding=(1, 2)))
        if debate_state.get("judge_decision"):
            research_reports.append(Panel(Markdown(debate_state["judge_decision"]), title="Research Manager", border_style="blue", padding=(1, 2)))
        if research_reports:
            console.print(Panel(Columns(research_reports, equal=True, expand=True), title="II. Research Team Decision", border_style="magenta", padding=(1, 2)))

    # III. Trading Team Reports
    if final_state.get("trader_investment_plan"):
        console.print(Panel(Panel(Markdown(final_state["trader_investment_plan"]), title="Trader", border_style="blue", padding=(1, 2)), title="III. Trading Team Plan", border_style="yellow", padding=(1, 2)))

    # IV-V. Risk Management and Portfolio Manager
    if final_state.get("risk_debate_state"):
        risk_reports = []
        risk_state = final_state["risk_debate_state"]
        if risk_state.get("risky_history"):
            risk_reports.append(Panel(Markdown(risk_state["risky_history"]), title="Aggressive Analyst", border_style="blue", padding=(1, 2)))
        if risk_state.get("safe_history"):
            risk_reports.append(Panel(Markdown(risk_state["safe_history"]), title="Conservative Analyst", border_style="blue", padding=(1, 2)))
        if risk_state.get("neutral_history"):
            risk_reports.append(Panel(Markdown(risk_state["neutral_history"]), title="Neutral Analyst", border_style="blue", padding=(1, 2)))
        if risk_reports:
            console.print(Panel(Columns(risk_reports, equal=True, expand=True), title="IV. Risk Management Team Decision", border_style="red", padding=(1, 2)))
        if risk_state.get("judge_decision"):
            console.print(Panel(Panel(Markdown(risk_state["judge_decision"]), title="Portfolio Manager", border_style="blue", padding=(1, 2)), title="V. Portfolio Manager Decision", border_style="green", padding=(1, 2)))


