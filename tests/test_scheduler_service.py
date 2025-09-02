import pytest

from app_email.analysis.analysis import run_analysis
from app_email.scheduler_service import load_due_jobs
from app_email.scheduler_service import process_job


def add(num1, num2):
    return num1 + num2

@pytest.mark.parametrize("num1, num2, expected", [
    (1, 1, 2),
    (2, 2, 4),
    (3, 3, 6),
    (4, 4, 8),
    (5, 5, 10),
    (6, 6, 12),
    (7, 7, 14),
    (8, 8, 16),
    (9, 9, 18),
])

def test_add(num1, num2, expected):
    print(num1, num2, expected)
    assert add(num1, num2) == expected


def test_load_due_jobs():
    jobs = load_due_jobs()
    if jobs:
        assert len(jobs) > 0
    print(jobs)

def test_process_job():
    rows = [
        {
            "id": 1,
            "user_id": 1,
            "ticker": "北方稀土",
            "ticker_identifier": "600111",
            "analysts": [
                "Market Analyst",
                "Financial Analyst"
            ],
            "research_depth": 1,
            "trigger_type": "interval",
            "interval_seconds": 3600,
            "cron_expr":  None,
            "next_run_at": "2025-09-01 15:25:48",
            "active": 1,
            "created_at": "2025-09-01 03:07:23",
            "updated_at": "2025-09-01 15:25:48",
            "email": "1363992060@qq.com",
            "balance": 52.0,
            "currency": "CNY"
        }
    ]
    for row in rows:
        process_job(row)

def test_process_job_mock(mocker):
    mock_run_analysis = mocker.patch("app_email.scheduler_service.run_analysis")
    rows = [
        {
            "id": 1,
            "user_id": 1,
            "ticker": "北方稀土",
            "ticker_identifier": "600111",
            "analysts": [
                "Market Analyst",
                "Financial Analyst"
            ],
            "research_depth": 1,
            "trigger_type": "interval",
            "interval_seconds": 3600,
            "cron_expr":  None,
            "next_run_at": "2025-09-01 15:25:48",
            "active": 1,
            "created_at": "2025-09-01 03:07:23",
            "updated_at": "2025-09-01 15:25:48",
            "email": "1363992060@qq.com",
            "balance": 52.0,
            "currency": "CNY"
        }
    ]
    process_job(rows[0])
    # 3. 断言：验证我们的模拟函数是否被如期调用
    # 验证 run_analysis 被调用了一次
    mock_run_analysis.assert_called_once()
    args, kwargs = mock_run_analysis.call_args
    print("args")
    print(args)