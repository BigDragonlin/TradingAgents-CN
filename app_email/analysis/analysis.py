import time
from tradingagents.utils.logging_manager import get_logger
from .keys import check_api_keys
from .testConfig import CONFIG
from .pipeline import AnalysisPipeline
from app_email.send_email.make_report2doc import MakeReport2Doc
logger = get_logger("cli")


def run_analysis():
    start_time = time.time()

    selections = CONFIG
    if not check_api_keys(selections["llm_provider"]):
        logger.error("分析终止 | Analysis terminated")
        return

    logger.info("准备分析环境 | Preparing Analysis Environment")
    logger.info(f"正在分析股票: {selections['ticker']}")
    logger.info(f"分析日期: {selections['analysis_date']}")
    logger.info(f"选择的分析师: {', '.join(analyst.value for analyst in selections['analysts'])}")

    pipeline = AnalysisPipeline(selections)
    pipeline.configure()
    try:
        pipeline.init_graph()
    except Exception:
        return
    pipeline.prepare_outputs()
    message_buffer = pipeline.setup_message_buffer()

    if not pipeline.validate_data():
        return

    trace = pipeline.run_stream()
    pipeline.process_decision(trace)
    pipeline.generate_report()

    make_report2doc = MakeReport2Doc()
    make_report2doc.make_report2doc(selections['ticker'])

    total_time = time.time() - start_time
    logger.info(f"⏱️ 总分析时间: {total_time:.1f}秒")


