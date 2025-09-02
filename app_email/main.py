
from tradingagents.utils.scheduler import SchedulerManager
from app_email.scheduler_service import poll_and_run_jobs


def main():
    manager = SchedulerManager()
    manager.add_function(poll_and_run_jobs)
    manager.run()


if __name__ == "__main__":
    main()