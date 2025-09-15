import pytest
from app_email.email_receive_service import EmailReceiveService
import asyncio
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def email_receive_service():
    return EmailReceiveService()

# 测试发送邮件
def test_send_email(email_receive_service):
    to_email = "1363992060@qq.com"
    subject = "test subject"
    body_html = "test body html"
    email_receive_service.send_email(to_email, subject, body_html)
    # email_receive_service.send_email("test@test.com", "test", "test")
    # assert email_receive_service.send_email.called
    # assert email_receive_service.send_email.call_args.kwargs["to_email"] == "test@test.com"
    # assert email_receive_service.send_email.call_args.kwargs["subject"] == "test"
    # assert email_receive_service.send_email.call_args.kwargs["body_html"] == "test"
    
# 测试邮件回执
def test_send_email_receipt(mocker, email_receive_service):
    to_email = "1363992060@qq.com"
    mocker_count_pending_processing = mocker.patch("app_email.email_receive_service.count_pending_processing", return_value=1)
    
    mocker_send_email: MagicMock = mocker.patch("app_email.email_receive_service.send_email", return_value=True)
    email_receive_service.send_email_receipt(to_email)

    mocker_count_pending_processing.assert_called_once()
    mocker_send_email.assert_called_once()
    
    args, kwargs = mocker_send_email.call_args_list[0]
    assert kwargs["from_addr"] == email_receive_service.username

# 测试查询数据库表
def test_check_balance(mocker, email_receive_service):
    balance = email_receive_service.check_balance("1363992060@qq.com")
    assert balance > 0  
    

# 测试处理余额逻辑
def test_handle_balance(mocker, email_receive_service):
    to_email = "1363992060@qq.com"
    mocker_check_balance = mocker.patch("app_email.email_receive_service.EmailReceiveService.check_balance", return_value=100)
    is_success = email_receive_service.handle_balance(to_email)
    mocker_check_balance.assert_called_once()
    assert is_success == True

# 测试处理余额逻辑，余额不足
def test_handle_balance_balance_not_enough(mocker, email_receive_service):
    to_email = "1363992060@qq.com"
    mocker_check_balance = mocker.patch("app_email.email_receive_service.EmailReceiveService.check_balance", return_value=0)
    email_receive_service.handle_balance(to_email)
    mocker_check_balance.assert_called_once()

# 测试异步发送邮件回执，处理邮件
def test_send_email_receipt_async(mocker, email_receive_service):
    to_email = "1363992060@qq.com"
    # 注意这里调用的是异步函数new_callable=AsyncMock
    mocker_send_email_receipt = mocker.patch("app_email.email_receive_service.EmailReceiveService.send_email_receipt", new_callable=AsyncMock)
    mocker_process_email_job = mocker.patch("app_email.email_receive_service.process_email_job", new_callable=AsyncMock)
    asyncio.run(email_receive_service.send_email_receipt_async(to_email, "test_body"))

    mocker_process_email_job.assert_called_once()
    mocker_send_email_receipt.assert_called_once()

# 测试扣除余额
def test_debit_balance(mocker, email_receive_service):
    to_email = "1363992060@qq.com"
    mocker_estimate_cost = mocker.patch("app_email.email_receive_service.EmailReceiveService.estimate_cost", return_value=10)
    mocker_debit_balance = mocker.patch("app_email.email_receive_service.debit_balance")

    email_receive_service.debit_balance(to_email, "test_body")
    mocker_estimate_cost.assert_called_once()
    mocker_debit_balance.assert_called_once()

# 测试插入队列
def test_poll_emails(mocker, email_receive_service):
    mocker_receive_emails = mocker.patch("app_email.email_receive_service.receive_emails", 
                                         return_value=[
                                             {"from": "test@test.com", "subject": "test_subject", "body": "test_body", "id": "1"}])
    mocker_mark_email_as_seen = mocker.patch("app_email.email_receive_service.mark_email_as_seen", return_value=True)
    mocker_handle_balance = mocker.patch("app_email.email_receive_service.EmailReceiveService.handle_balance", return_value=True)
    mocker_send_email_receipt = mocker.patch("app_email.email_receive_service.EmailReceiveService.send_email_receipt_async", new_callable=AsyncMock)
    
    email_receive_service.poll_emails()

    mocker_receive_emails.assert_called_once()
    mocker_mark_email_as_seen.assert_called_once()
    mocker_handle_balance.assert_called_once()
    mocker_send_email_receipt.assert_called_once()

    kwargs = mocker_send_email_receipt.call_args_list[0].kwargs
    assert kwargs[0] == "test@test.com"
    assert kwargs[1] == "test_body"
