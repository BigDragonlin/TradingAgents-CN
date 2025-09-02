import sqlite3
import os

class Database:
    """
    一个用于管理 SQLite 数据库连接和操作的封装类。
    支持使用 'with' 语句自动管理连接。
    """

    def __init__(self, db_path):
        """
        初始化数据库类。
        :param db_path: 数据库文件的路径 (例如: 'my_project.db')。
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect(self):
        """建立数据库连接并创建游标。"""
        try:
            dir_name = os.path.dirname(self.db_path)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name,exist_ok=True)
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            print(f"成功连接到数据库: {self.db_path}")
        except sqlite3.Error as e:
            print(f"连接数据库时发生错误: {e}")
            raise  # 重新抛出异常，以便调用者可以处理

    def close(self):
        """关闭数据库连接。"""
        if self.conn:
            # 先关闭游标，再关闭连接是一种好习惯
            if self.cursor:
                self.cursor.close()
            self.conn.close()
            self.conn = None
            print("数据库连接已关闭。")

    def commit(self):
        """提交当前事务。"""
        if self.conn:
            self.conn.commit()
            print("事务已成功提交。")
        else:
            print("没有活动的数据库连接，无法提交。")

    def execute(self, sql_query, params=None):
        """
        执行一条 SQL 语句。
        :param sql_query: 要执行的 SQL 字符串。
        :param params: (可选) SQL 查询的参数，用于防止 SQL 注入。
        :return: 返回游标对象，以便获取查询结果。
        """
        if not self.cursor:
            print("没有活动的游标，无法执行命令。")
            return None

        try:
            if params:
                self.cursor.execute(sql_query, params)
            else:
                self.cursor.execute(sql_query)
            return self.cursor
        except sqlite3.Error as e:
            print(f"执行 SQL 时发生错误: {e}")
            return None

    # --- 上下文管理器支持 ---

    def __enter__(self):
        """上下文管理器的进入方法，建立连接并返回自身。"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器的退出方法，自动提交或回滚并关闭连接。
        :param exc_type: 异常类型
        :param exc_val: 异常值
        :param exc_tb: 异常的追溯信息
        """
        if exc_type is None and self.conn:
            # 如果没有发生异常，则提交事务
            self.commit()
        else:
            # 如果发生了异常，打印错误信息（默认不回滚，因为 sqlite3 会自动处理）
            print(f"发生异常: {exc_val}。事务将不会被提交。")

        # 无论如何，最后都关闭连接
        self.close()