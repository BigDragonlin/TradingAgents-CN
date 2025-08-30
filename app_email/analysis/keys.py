import os
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("cli")


def check_api_keys(llm_provider: str) -> bool:
    """检查必要的API密钥是否已配置。"""
    missing_keys = []

    prov = llm_provider.lower()
    if "阿里百炼" in llm_provider or "dashscope" in prov:
        if not os.getenv("DASHSCOPE_API_KEY"):
            missing_keys.append("DASHSCOPE_API_KEY (阿里百炼)")
    elif "openai" in prov:
        if not os.getenv("OPENAI_API_KEY"):
            missing_keys.append("OPENAI_API_KEY")
    elif "anthropic" in prov:
        if not os.getenv("ANTHROPIC_API_KEY"):
            missing_keys.append("ANTHROPIC_API_KEY")
    elif "google" in prov:
        if not os.getenv("GOOGLE_API_KEY"):
            missing_keys.append("GOOGLE_API_KEY")

    if not os.getenv("FINNHUB_API_KEY"):
        missing_keys.append("FINNHUB_API_KEY (金融数据)")

    if missing_keys:
        logger.error("[red]❌ 缺少必要的API密钥 | Missing required API keys[/red]")
        for key in missing_keys:
            logger.info(f"   • {key}")
        logger.info(f"\n[yellow]💡 解决方案 | Solutions:[/yellow]")
        logger.info(f"1. 在项目根目录创建 .env 文件 | Create .env file in project root:")
        logger.info(f"   DASHSCOPE_API_KEY=your_dashscope_key")
        logger.info(f"   FINNHUB_API_KEY=your_finnhub_key")
        logger.info(f"\n2. 或设置环境变量 | Or set environment variables")
        logger.info(f"\n3. 运行 'python -m cli.main config' 查看详细配置说明")
        return False
    return True


