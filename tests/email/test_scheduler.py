from tradingagents.utils.scheduler import SchedulerManager
import datetime

def hello_world_job():
    """
    一个简单的任务函数，打印'Hello, World!'和当前时间。
    """
    print(f"Hello, World! 当前时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")



def test_scheduler():
    manager = SchedulerManager()
    manager.add_function(hello_world_job)
    manager.run()