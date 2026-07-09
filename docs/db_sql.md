# SQL 数据库操作模块

> 本文档介绍 `baibao.db.sql` 模块的使用方法，提供统一的数据库操作接口。

## 模块概述

`baibao.db.sql` 模块提供了简洁的数据库操作接口，支持 MySQL 和 PostgreSQL。主要特点：

- 统一的 API 接口，简化数据库操作
- 自动管理连接生命周期（获取、使用、归还）
- 支持多数据源配置
- 参数化查询防止 SQL 注入
- 自动处理事务提交和回滚

## 基本使用

### 导入模块

推荐直接从 `baibao` 导入 `sql`、`DbCfg`、`DbClient`：

```python
from baibao import sql, DbCfg, DbClient
# 或者通过子模块导入
# from baibao.db import sql, DbCfg, DbClient
```

### 数据库配置

使用 `DbCfg` 类创建数据库配置：

```python
from baibao import DbCfg

# 直接构造配置
cfg = DbCfg(
    host="localhost",
    port=3306,
    username="root",
    password="your_password",
    database="your_database",
    db_type="mysql",      # 支持 "mysql"、"postgresql"，默认 "mysql"
    charset="utf8mb4"     # 默认 utf8mb4
)

# 从 JSON 文件加载配置
cfg = DbCfg.load_from_json_cfg("db.config")
```

`db.config` 文件示例：

```json
{
    "host": "localhost",
    "port": 3306,
    "username": "root",
    "password": "your_password",
    "database": "your_database",
    "db_type": "mysql"
}
```

## 数据库客户端管理

### 设置客户端

```python
from baibao import sql, DbCfg, DbClient

# 使用 DbCfg 设置（自动创建 DbClient，默认使用连接池模式）
cfg = DbCfg(host="localhost", port=3306, username="root",
            password="123456", database="test_db")
sql.set_client("my_db", cfg)

# 或直接使用 DbClient 设置（可自定义连接池参数）
client = DbClient(cfg, use_pool=True,
                  mincached=1,       # 最小空闲连接数
                  maxcached=10,      # 最大空闲连接数
                  maxconnections=20) # 最大总连接数
sql.set_client("my_db", client)
```

#### 连接模式说明

**连接池模式（默认）**：适合高并发场景，线程安全
- 基于 DBUtils.PooledDB 实现
- 连接使用后归还到连接池，不会真正关闭
- 可配置最小/最大空闲连接数和最大总连接数

**单连接模式**：适合低并发或资源受限场景，非线程安全，仅限单线程使用
- 使用单个数据库连接
- 返回代理对象，防止调用方误关闭共享连接
- 连接的生命周期由 DbClient 统一管理

```python
# 使用单连接模式
client = DbClient(cfg, use_pool=False)
sql.set_client("my_db", client)
```

### 获取客户端

```python
# 获取指定配置名的客户端
client = sql.get_client("my_db")

# 获取默认配置名的客户端（自动从 ./db.config 加载）
client = sql.get_client()
```

### 移除客户端

```python
# 移除指定配置名的客户端
sql.remove_client("my_db")

# 移除默认配置名的客户端
sql.remove_client()
```

### 清空所有客户端

```python
# 清空所有数据库客户端
sql.clear()
```

## 执行 SQL 操作

### 执行写操作（INSERT/UPDATE/DELETE）

使用 `exec()` 方法执行写操作，自动提交事务：

```python
from baibao import sql

# 插入数据
affected_rows = sql.exec(
    "INSERT INTO users (name, email) VALUES (%s, %s)",
    params=("张三", "zhangsan@example.com")
)
print(f"插入了 {affected_rows} 行")

# 更新数据
affected_rows = sql.exec(
    "UPDATE users SET email = %s WHERE name = %s",
    params=("new_email@example.com", "张三")
)

# 删除数据
affected_rows = sql.exec(
    "DELETE FROM users WHERE name = %s",
    params=("张三",)
)
```

### 执行查询操作（SELECT）

使用 `query()` 方法执行查询，返回结果列表：

```python
from baibao import sql

# 查询所有用户
users = sql.query("SELECT * FROM users")
for user in users:
    print(user)  # {'id': 1, 'name': '张三', 'email': 'zhangsan@example.com'}

# 带参数的查询
users = sql.query(
    "SELECT * FROM users WHERE name = %s",
    params=("张三",)
)

# 查询单个字段
emails = sql.query("SELECT email FROM users")
for row in emails:
    print(row['email'])

# 将 Decimal 类型转换为 float（适用于金额等字段）
orders = sql.query(
    "SELECT * FROM orders WHERE amount > %s",
    params=(100,),
    to_float=True  # Decimal 字段会自动转换为 float
)
```

## 多数据源管理

支持同时管理多个数据库连接：

```python
from baibao import sql, DbCfg, DbClient
# 或者通过子模块导入
# from baibao.db import sql, DbCfg, DbClient

# 配置主数据库
main_cfg = DbCfg(
    host="localhost",
    port=3306,
    username="root",
    password="123456",
    database="main_db"
)

# 配置日志数据库
log_cfg = DbCfg(
    host="localhost",
    port=3306,
    username="root",
    password="123456",
    database="log_db"
)

# 注册多个数据源
sql.set_client("main", main_cfg)
sql.set_client("log", log_cfg)

# 使用指定数据源执行操作
users = sql.query("SELECT * FROM users", cfg_name="main")
logs = sql.query("SELECT * FROM access_logs", cfg_name="log")

# 在指定数据源执行写操作
sql.exec(
    "INSERT INTO access_logs (user_id, action) VALUES (%s, %s)",
    params=(1, "login"),
    cfg_name="log"
)
```

## 完整示例

```python
from baibao import sql, DbCfg, DbClient
# 或者通过子模块导入
# from baibao.db import sql, DbCfg, DbClient

def main():
    # 1. 配置数据库连接
    cfg = DbCfg(
        host="localhost",
        port=3306,
        username="root",
        password="your_password",
        database="test_db",
        db_type="mysql"
    )
    
    # 2. 设置数据库客户端
    sql.set_client("test", cfg)
    
    try:
        # 3. 创建表
        sql.exec("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(200) UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """, cfg_name="test")
        
        # 4. 插入数据
        affected = sql.exec(
            "INSERT INTO users (name, email) VALUES (%s, %s)",
            params=("李四", "lisi@example.com"),
            cfg_name="test"
        )
        print(f"插入了 {affected} 条记录")
        
        # 5. 查询数据
        users = sql.query(
            "SELECT * FROM users WHERE name = %s",
            params=("李四",),
            cfg_name="test"
        )
        print(f"查询到 {len(users)} 条记录")
        
        # 6. 更新数据
        sql.exec(
            "UPDATE users SET email = %s WHERE name = %s",
            params=("new_email@example.com", "李四"),
            cfg_name="test"
        )
        
        # 7. 删除数据
        sql.exec(
            "DELETE FROM users WHERE name = %s",
            params=("李四",),
            cfg_name="test"
        )
        
    except Exception as e:
        print(f"操作失败: {e}")
    
    finally:
        # 8. 清理资源
        sql.remove_client("test")

if __name__ == "__main__":
    main()
```

## 注意事项

1. **参数化查询**：始终使用 `%s` 占位符和 `params` 参数，避免 SQL 注入
2. **连接管理**：`exec()` 和 `query()` 方法会自动管理连接生命周期，无需手动关闭
3. **事务处理**：`exec()` 方法自动提交事务，异常时自动回滚
4. **配置文件**：默认配置会从 `./db.config` 文件加载，确保文件路径正确
5. **字符集**：MySQL 默认使用 `utf8mb4` 字符集，支持完整的 Unicode 字符

## 错误处理

```python
from baibao import sql

try:
    # 尝试执行数据库操作
    result = sql.query("SELECT * FROM non_existent_table")
except KeyError as e:
    print(f"配置错误: {e}")
except Exception as e:
    print(f"数据库操作失败: {e}")
```