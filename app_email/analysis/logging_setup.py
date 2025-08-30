def setup_cli_logging():
    """
    CLI模式下的日志配置：移除控制台输出，保持界面清爽
    Configure logging for CLI mode: remove console output to keep interface clean
    """
    import logging
    from tradingagents.utils.logging_manager import get_logger_manager

    logger = logging.getLogger("cli")
    logger_manager = get_logger_manager()

    # 获取根日志器
    root_logger = logging.getLogger()

    # 移除所有控制台处理器，只保留文件日志
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and hasattr(handler, 'stream'):
            if getattr(handler.stream, 'name', None) in ['<stderr>', '<stdout>']:
                root_logger.removeHandler(handler)

    # 同时移除tradingagents日志器的控制台处理器
    tradingagents_logger = logging.getLogger('tradingagents')
    for handler in tradingagents_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and hasattr(handler, 'stream'):
            if getattr(handler.stream, 'name', None) in ['<stderr>', '<stdout>']:
                tradingagents_logger.removeHandler(handler)

    # 记录CLI启动日志（只写入文件）
    from tradingagents.utils.logging_manager import get_logger
    get_logger("cli").debug("🚀 CLI模式启动，控制台日志已禁用，保持界面清爽")


