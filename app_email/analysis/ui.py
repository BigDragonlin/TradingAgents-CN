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



