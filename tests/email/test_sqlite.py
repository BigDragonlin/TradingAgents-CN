# test_database.py
import unittest
import sqlite3
import os
from tradingagents.utils.database import Database # 从您的 database.py 文件中导入 Database 类

class TestDatabase(unittest.TestCase):
    """测试 Database 类的测试用例集"""

    def setUp(self):
        """
        在每个测试方法运行前执行。
        负责创建一个临时的测试数据库。
        """
        # self.db_file = 'datatest_temp.db'
        self.db_file = 'data/sqlite/test_temp.db'
        # 确保每次测试开始前，旧的测试数据库文件都被删除
        # if os.path.exists(self.db_file):
        #     os.remove(self.db_file)

    def tearDown(self):
        """
        在每个测试方法运行后执行。
        负责删除测试数据库，清理环境。
        """
        # if os.path.exists(self.db_file):
        #     os.remove(self.db_file)

    def test_01_connection_and_file_creation(self):
        """测试：数据库连接是否能成功创建数据库文件。"""
        self.assertFalse(os.path.exists(self.db_file)) # 确认文件初始不存在

        # 使用 with 语句会自动连接和关闭
        with Database(self.db_file) as db:
            # 在 with 代码块内部，文件应该已经被创建
            self.assertTrue(os.path.exists(self.db_file))

        # with 代码块结束后，文件仍然存在
        self.assertTrue(os.path.exists(self.db_file))
        print("\n[PASS] test_01_connection_and_file_creation")

    def test_02_create_table_and_commit(self):
        """测试：执行 CREATE TABLE 语句并自动提交。"""
        create_table_query = '''
        CREATE TABLE test_users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        '''
        with Database(self.db_file) as db:
            db.execute(create_table_query)

        # 重新连接数据库（不通过我们的类），以验证表是否真的被创建并提交了
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        # 查询 sqlite_master 表，这是 SQLite 存储数据库结构的地方
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_users';")
        result = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(result) # 如果结果不是 None，说明表存在
        self.assertEqual(result[0], 'test_users')
        print("[PASS] test_02_create_table_and_commit")

    def test_03_insert_and_select_data(self):
        """测试：插入数据并能成功查询到。"""
        create_table_query = "CREATE TABLE test_users (id INTEGER PRIMARY KEY, name TEXT NOT NULL);"
        insert_query = "INSERT INTO test_users (id, name) VALUES (?, ?);"
        select_query = "SELECT name FROM test_users WHERE id = ?;"

        with Database(self.db_file) as db:
            db.execute(create_table_query)
            db.execute(insert_query, (1, 'Alice'))

            # 在同一个连接中查询
            cursor = db.execute(select_query, (1,))
            result = cursor.fetchone()

        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'Alice')
        print("[PASS] test_03_insert_and_select_data")

    def test_04_context_manager_rolls_back_on_error(self):
        """测试：当 with 代码块内发生异常时，事务是否会自动回滚。"""
        create_table_query = "CREATE TABLE test_users (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);"
        insert_query = "INSERT INTO test_users (id, name) VALUES (?, ?);"

        # 我们期望 with 代码块会抛出 IntegrityError 异常
        with self.assertRaises(sqlite3.IntegrityError):
            with Database(self.db_file) as db:
                db.execute(create_table_query)
                db.execute(insert_query, (1, 'Bob')) # 第一次插入，应该成功
                db.execute(insert_query, (2, 'Bob')) # 第二次插入，name不是唯一的，会失败

        # 验证第一次的插入是否被回滚
        # 因为第二次插入失败导致了异常，整个事务（包括第一次的插入）都不应该被提交
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM test_users WHERE id = 1;")
        result = cursor.fetchone()
        conn.close()

        self.assertIsNone(result) # 如果结果是 None，说明 'Bob' 没有被插入，回滚成功
        print("[PASS] test_04_context_manager_rolls_back_on_error")

    def test_05_manual_commit_and_close(self):
        """测试：不使用 'with' 语句，手动调用方法。"""
        db = Database(self.db_file)
        try:
            db.connect()
            self.assertIsNotNone(db.conn)
            self.assertIsNotNone(db.cursor)

            db.execute("CREATE TABLE manual_test (id INTEGER);")
            db.execute("INSERT INTO manual_test (id) VALUES (100);")
            db.commit() # 手动提交

            # 验证数据已提交
            cursor = db.execute("SELECT id FROM manual_test WHERE id = 100;")
            result = cursor.fetchone()
            self.assertEqual(result[0], 100)

        finally:
            db.close() # 手动关闭
            self.assertIsNone(db.conn, "数据库连接在 close() 后应为 None")
        print("[PASS] test_05_manual_commit_and_close")


# 这使得测试文件可以直接从命令行运行
if __name__ == '__main__':
    unittest.main(verbosity=2)
