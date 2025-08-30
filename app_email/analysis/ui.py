from rich.console import Console
from rich.panel import Panel
from rich.align import Align

from tradingagents.utils.logging_manager import get_logger


class CLIUserInterface:
    """CLI用户界面管理器：处理用户显示和进度提示"""

    def __init__(self):
        self.console = Console()
        self.logger = get_logger("cli")

    def show_user_message(self, message: str, style: str = ""):
        if style:
            self.console.print(f"[{style}]{message}[/{style}]")
        else:
            self.console.print(message)

    def show_progress(self, message: str):
        self.console.print(f"🔄 {message}")
        self.logger.info(f"进度: {message}")

    def show_success(self, message: str):
        self.console.print(f"[green]✅ {message}[/green]")
        self.logger.info(f"成功: {message}")

    def show_error(self, message: str):
        self.console.print(f"[red]❌ {message}[/red]")
        self.logger.error(f"错误: {message}")

    def show_warning(self, message: str):
        self.console.print(f"[yellow]⚠️ {message}[/yellow]")
        self.logger.warning(f"警告: {message}")

    def show_step_header(self, step_num: int, title: str):
        self.console.print(f"\n[bold cyan]步骤 {step_num}: {title}[/bold cyan]")
        self.console.print("─" * 60)


def print_welcome(console: Console):
    from pathlib import Path
    try:
        with open(Path(__file__).parent / "static" / "welcome.txt", "r", encoding="utf-8") as f:
            welcome_ascii = f.read()
    except FileNotFoundError:
        welcome_ascii = "TradingAgents"

    welcome_content = f"{welcome_ascii}\n"
    welcome_content += "[bold green]TradingAgents: 多智能体大语言模型金融交易框架 - CLI[/bold green]\n"
    welcome_content += "[bold green]Multi-Agents LLM Financial Trading Framework - CLI[/bold green]\n\n"
    welcome_content += "[bold]工作流程 | Workflow Steps:[/bold]\n"
    welcome_content += "I. 分析师团队 | Analyst Team → II. 研究团队 | Research Team → III. 交易员 | Trader → IV. 风险管理 | Risk Management → V. 投资组合管理 | Portfolio Management\n\n"
    welcome_content += ("[dim]Built by [Tauric Research](https://github.com/TauricResearch)[/dim]")

    welcome_box = Panel(
        welcome_content,
        border_style="green",
        padding=(1, 2),
        title="欢迎使用 TradingAgents | Welcome to TradingAgents",
        subtitle="多智能体大语言模型金融交易框架 | Multi-Agents LLM Financial Trading Framework",
    )
    console.print(Align.center(welcome_box))
    console.print()


