import duckdb
from threading import Lock
import threading

class DuckDBConnectionPool:
    def __init__(self, max_connections=10):
        self.max_connections = max_connections
        self.connections = []
        self.lock = Lock()
        self.active_connections = 0
        
    def get_connection(self):
        with self.lock:
            if self.connections:
                return self.connections.pop()
            elif self.active_connections < self.max_connections:
                self.active_connections += 1
                return duckdb.connect(':memory:')  # 或者连接到文件
            else:
                raise Exception("Maximum connections reached")
    
    def release_connection(self, conn):
        with self.lock:
            if len(self.connections) < self.max_connections:
                self.connections.append(conn)
            else:
                # 如果连接池已满，关闭连接
                conn.close()
                self.active_connections -= 1

# 使用示例
duckdb_pool = DuckDBConnectionPool(max_connections=5)

# 获取连接
conn = pool.get_connection()
try:
    # 执行查询
    result = conn.execute("SELECT 1").fetchall()
    print(result)
finally:
    # 释放连接
    pool.release_connection(conn)
