import pytest
from app_email.scheduler_service import *
from unittest.mock import MagicMock
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

def test_count_pending_processing():
    count = count_pending_processing()
    print("数量")
    print(count)

# 测试消耗处理
def test_consume_balance(mocker):
    mocker_debit_balance = mocker.patch("app_email.scheduler_service.debit_balance", return_value=100)
    mocker_send_email: MagicMock = mocker.patch("app_email.scheduler_service.send_email")
    consume_balance("test@test.com", 10)
    mocker_debit_balance.assert_called_once()
    mocker_send_email.assert_called_once()
    
    list = mocker_send_email.call_args_list[0].kwargs
    assert list["to_addrs"] == ["test@test.com"]
    assert list["subject"] == "余额还有100"
    assert list["body_html"] == "余额还有100"

def test_enqueue_email(mocker):
    enqueue_email("test@test.com", "test_subject", "test_body")
