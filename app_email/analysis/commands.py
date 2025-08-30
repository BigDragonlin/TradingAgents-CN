import os
import sys
import subprocess
from difflib import get_close_matches

import typer
from rich.table import Table

from tradingagents.utils.logging_manager import get_logger
from .analysis import run_analysis


app = typer.Typer(
    name="TradingAgents",
    help="TradingAgents CLI: 多智能体大语言模型金融交易框架 | Multi-Agents LLM Financial Trading Framework",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=False,
)

logger = get_logger("cli")


@app.command(name="analyze", help="开始股票分析 | Start stock analysis")
def analyze():
    run_analysis()


@app.command(name="version", help="版本信息 | Version information")
def version():
    try:
        with open("VERSION", "r", encoding="utf-8") as f:
            version = f.read().strip()
    except FileNotFoundError:
        version = "1.0.0"
    logger.info(f"\n[bold blue]📊 TradingAgents 版本信息 | Version Information[/bold blue]")
    logger.info(f"[green]版本 | Version:[/green] {version} [yellow](预览版 | Preview)[/yellow]")


@app.command(name="test", help="运行测试 | Run tests")
def test():
    logger.info(f"\n[bold blue]🧪 TradingAgents 测试 | Tests[/bold blue]")
    logger.info(f"[yellow]正在运行集成测试... | Running integration tests...[/yellow]")
    try:
        result = subprocess.run([sys.executable, "tests/integration/test_dashscope_integration.py"], capture_output=True, text=True, cwd=".")
        if result.returncode == 0:
            logger.info(f"[green]✅ 测试通过 | Tests passed[/green]")
        else:
            logger.error(f"[red]❌ 测试失败 | Tests failed[/red]")
    except Exception as e:
        logger.error(f"[red]❌ 测试执行错误 | Test execution error: {e}[/red]")


def main_with_args():
    if len(sys.argv) == 1:
        run_analysis()
        return
    try:
        app()
    except SystemExit as e:
        if e.code == 2 and len(sys.argv) > 1:
            unknown_command = sys.argv[1]
            available_commands = ['analyze', 'config', 'version', 'data-config', 'examples', 'test', 'help']
            suggestions = get_close_matches(unknown_command, available_commands, n=3, cutoff=0.6)
            if suggestions:
                logger.error(f"\n[red]❌ 未知命令: '{unknown_command}'[/red]")
                logger.info(f"[yellow]💡 您是否想要使用以下命令之一？[/yellow]")
                for suggestion in suggestions:
                    logger.info(f"   • [cyan]python -m cli.main {suggestion}[/cyan]")
            else:
                logger.error(f"\n[red]❌ 未知命令: '{unknown_command}'[/red]")
        raise e


