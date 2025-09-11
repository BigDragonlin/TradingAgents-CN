import pytest
from app_email.scheduler_service import process_email_job
@pytest.fixture
def scheduler_service():
    receiveBody = """
{
&nbsp; &nbsp; "股票代码": "000831",
&nbsp; &nbsp; "分析师": [
&nbsp; &nbsp; &nbsp; &nbsp; "市场分析",
&nbsp; &nbsp; &nbsp; &nbsp; "新闻分析",
&nbsp; &nbsp; &nbsp; &nbsp; "基本面分析"
&nbsp; &nbsp; ],
&nbsp; &nbsp; "研究深度": 1
}
"""
    return receiveBody

def test_process_email_job(scheduler_service):
    process_email_job(scheduler_service, "test@test.com")