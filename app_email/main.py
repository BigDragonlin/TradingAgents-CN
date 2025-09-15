from tradingagents.utils.scheduler import SchedulerManager
from app_email.scheduler_service import poll_and_run_jobs, consume_email_queue_batch
from app_email.email_receive_service import poll_and_receive_emails
from app_email.scheduler_service import ensure_email_queue_table

def main():
    ensure_email_queue_table()
    manager = SchedulerManager()
    # 切换为每周一至周五 08:30 运行
    # manager.add_weekday_0830(poll_and_run_jobs)
    # manager.add_daily_0830(poll_and_run_jobs)
    # manager.add_function(poll_and_run_jobs)
    manager.add_function(poll_and_receive_emails)
    # 处理队列中的任务
    manager.scheduler.add_job(
        consume_email_queue_batch,
        trigger='interval',
        seconds=30,
        id='consume_email_queue_batch'
    )
    manager.run()


if __name__ == "__main__":
    main()
