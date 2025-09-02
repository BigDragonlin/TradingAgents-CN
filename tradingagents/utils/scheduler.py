import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

class SchedulerManager:
    """
    一个用于管理 APScheduler 的封装类。
    """
    def __init__(self, timezone="Asia/Shanghai"):
        """
        初始化调度器。
        - 使用 BlockingScheduler，它会在一个专用的前台线程中运行，适合独立的定时任务脚本。
        - 强烈建议设置时区，以避免因服务器时区不同导致的混淆。
        """
        self.scheduler = BlockingScheduler(timezone=timezone)

    def add_function(self, function):
        """
        添加自定义任务任务。
        任务规则：每10秒执行一次。
        """
        print("正在添加自定义任务...")
        self.scheduler.add_job(
            function,      # 要执行的函数
            trigger='interval',       # 使用 cron 触发器
            seconds=10,           # 触发条件：10秒
            id='custom_job_01' # 为任务分配一个唯一的ID
        )
        print("任务添加成功！规则：每10秒执行一次。")

    def run(self):
        """
        启动调度器并处理退出事件。
        """
        print("调度器已启动... 按下 Ctrl+C 即可退出程序。")
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print("收到退出指令，正在关闭调度器...")
            self.scheduler.shutdown()
            print("调度器已关闭。")