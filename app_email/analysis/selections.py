import datetime
import typer
from rich.panel import Panel

from .ui import print_welcome
from .utils import (
    select_analysts,
    select_deep_thinking_agent,
    select_llm_provider,
    select_research_depth,
    select_shallow_thinking_agent,
)


def select_market(console):
    markets = {
        "1": {
            "name": "美股",
            "name_en": "US Stock",
            "default": "SPY",
            "examples": ["SPY", "AAPL", "TSLA", "NVDA", "MSFT"],
            "format": "直接输入代码 (如: AAPL)",
            "pattern": r'^[A-Z]{1,5}$',
            "data_source": "yahoo_finance",
        },
        "2": {
            "name": "A股",
            "name_en": "China A-Share",
            "default": "600036",
            "examples": ["000001 (平安银行)", "600036 (招商银行)", "000858 (五粮液)"],
            "format": "6位数字代码 (如: 600036, 000001)",
            "pattern": r'^\d{6}$',
            "data_source": "china_stock",
        },
        "3": {
            "name": "港股",
            "name_en": "Hong Kong Stock",
            "default": "0700.HK",
            "examples": ["0700.HK (腾讯)", "09988.HK (阿里巴巴)", "03690.HK (美团)"],
            "format": "代码.HK (如: 0700.HK, 09988.HK)",
            "pattern": r'^\d{4,5}\.HK$',
            "data_source": "yahoo_finance",
        },
    }

    console.print(f"\n[bold cyan]请选择股票市场 | Please select stock market:[/bold cyan]")
    for key, market in markets.items():
        examples_str = ", ".join(market["examples"][:3])
        console.print(f"[cyan]{key}[/cyan]. 🌍 {market['name']} | {market['name_en']}")
        console.print(f"   示例 | Examples: {examples_str}")

    while True:
        choice = typer.prompt("\n请选择市场 | Select market", default="2")
        if choice in markets:
            selected_market = markets[choice]
            console.print(f"[green]✅ 已选择: {selected_market['name']} | Selected: {selected_market['name_en']}[/green]")
            return selected_market
        else:
            console.print(f"[red]❌ 无效选择，请输入 1、2 或 3 | Invalid choice, please enter 1, 2, or 3[/red]")


def get_ticker(console, market):
    console.print(f"\n[bold cyan]{market['name']}股票示例 | {market['name_en']} Examples:[/bold cyan]")
    for example in market['examples']:
        console.print(f"  • {example}")
    console.print(f"\n[dim]格式要求 | Format: {market['format']}[/dim]")

    import re
    while True:
        ticker = typer.prompt(f"\n请输入{market['name']}股票代码 | Enter {market['name_en']} ticker", default=market['default'])
        ticker = ticker.strip()
        if not ticker:
            console.print(f"[red]❌ 股票代码不能为空 | Ticker cannot be empty[/red]")
            continue
        ticker_to_check = ticker.upper() if market['data_source'] != 'china_stock' else ticker
        if re.match(market['pattern'], ticker_to_check):
            return ticker if market['data_source'] == 'china_stock' else ticker.upper()
        console.print(f"[red]❌ 股票代码格式不正确 | Invalid ticker format[/red]")
        console.print(f"[yellow]请使用正确格式: {market['format']}[/yellow]")


def get_analysis_date(console):
    while True:
        date_str = typer.prompt("请输入分析日期 | Enter analysis date", default=datetime.datetime.now().strftime("%Y-%m-%d"))
        try:
            analysis_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            if analysis_date.date() > datetime.datetime.now().date():
                console.print(f"[red]错误：分析日期不能是未来日期 | Error: Analysis date cannot be in the future[/red]")
                continue
            return date_str
        except ValueError:
            console.print("[red]错误：日期格式无效，请使用 YYYY-MM-DD 格式 | Error: Invalid date format. Please use YYYY-MM-DD[/red]")


def get_user_selections(console):
    print_welcome(console)

    selected_market = select_market(console)
    selected_ticker = get_ticker(console, selected_market)

    default_date = datetime.datetime.now().strftime("%Y-%m-%d")
    console.print(
        Panel(
            f"[bold]步骤 3: 分析日期 | Step 3: Analysis Date[/bold]\n[dim]请输入分析日期 (YYYY-MM-DD) | Enter the analysis date (YYYY-MM-DD)\nDefault: {default_date}[/dim]",
            border_style="blue",
            padding=(1, 2),
        )
    )
    analysis_date = get_analysis_date(console)

    console.print(Panel("[bold]步骤 4: 分析师团队 | Step 4: Analysts Team[/bold]\n[dim]选择您的LLM分析师智能体进行分析 | Select your LLM analyst agents for the analysis[/dim]", border_style="blue", padding=(1, 2)))
    selected_analysts = select_analysts()

    console.print(Panel("[bold]步骤 5: 研究深度 | Step 5: Research Depth[/bold]\n[dim]选择您的研究深度级别 | Select your research depth level[/dim]", border_style="blue", padding=(1, 2)))
    selected_research_depth = select_research_depth()

    console.print(Panel("[bold]步骤 6: LLM提供商 | Step 6: LLM Provider[/bold]\n[dim]选择要使用的LLM服务 | Select which LLM service to use[/dim]", border_style="blue", padding=(1, 2)))
    selected_llm_provider, backend_url = select_llm_provider()

    console.print(Panel("[bold]步骤 7: 思考智能体 | Step 7: Thinking Agents[/bold]\n[dim]选择您的思考智能体进行分析 | Select your thinking agents for analysis[/dim]", border_style="blue", padding=(1, 2)))
    selected_shallow_thinker = select_shallow_thinking_agent(selected_llm_provider)
    selected_deep_thinker = select_deep_thinking_agent(selected_llm_provider)

    return {
        "ticker": selected_ticker,
        "market": selected_market,
        "analysis_date": analysis_date,
        "analysts": selected_analysts,
        "research_depth": selected_research_depth,
        "llm_provider": selected_llm_provider.lower(),
        "backend_url": backend_url,
        "shallow_thinker": selected_shallow_thinker,
        "deep_thinker": selected_deep_thinker,
    }


