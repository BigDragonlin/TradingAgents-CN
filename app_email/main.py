
from tradingagents.utils.scheduler import SchedulerManager
from app_email.scheduler_service import poll_and_run_jobs


def main():
    poll_and_run_jobs()
    # manager = SchedulerManager()
    # # 切换为每周一至周五 08:30 运行
    # manager.add_weekday_0830(poll_and_run_jobs)
    # manager.add_daily_0830(poll_and_run_jobs)
    # manager.run()


if __name__ == "__main__":
    main()