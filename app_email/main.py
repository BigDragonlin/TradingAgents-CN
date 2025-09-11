from tradingagents.utils.scheduler import SchedulerManager
from app_email.scheduler_service import poll_and_run_jobs
from app_email.email_receive_service import poll_and_receive_emails


def main():
    manager = SchedulerManager()
    # 切换为每周一至周五 08:30 运行
    # manager.add_weekday_0830(poll_and_run_jobs)
    # manager.add_daily_0830(poll_and_run_jobs)
    # manager.add_function(poll_and_run_jobs)
    manager.add_function(poll_and_receive_emails)
    manager.run()


if __name__ == "__main__":
    main()
