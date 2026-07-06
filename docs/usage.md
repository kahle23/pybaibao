# BaiBao 使用示例

> 本文档包含所有模块的详细用法，方便开发者和 AI 快速理解和使用。

## 1. base.util - 动态导入模块

自动检测并安装缺失的 Python 包，安装失败时抛出 `ImportError`。

```python
from baibao.base import util

# 导入标准库（已存在，直接返回）
json = util.import_module("json")

# 导入第三方包（未安装时自动安装）
numpy = util.import_module("numpy")

# 模块名和安装包名不同时，分别指定
cv2 = util.import_module("cv2", install_name="opencv-python")
```

### 从 JSON 文件加载 dataclass 配置

通用方法，适用于任何 `dataclass` 定义的配置类。自动校验必填字段，缺少字段时抛出 `ValueError`。

```python
from dataclasses import dataclass
from baibao.base import util

@dataclass
class AppConfig:
    app_name: str
    debug: bool
    port: int = 8080

# 从 JSON 文件加载，自动校验 app_name、debug 是否存在
config = util.load_dataclass_from_json_file("config.json", AppConfig)
print(config.app_name, config.port)
```

对应的 `config.json`：

```json
{
    "app_name": "my-app",
    "debug": true
}
```

---

## 2. base.log - 日志

提供带颜色和级别的日志输出，支持 DEBUG / INFO / WARN / ERROR 四个级别，以及始终输出的 USAGE 级别。

```python
from baibao.base import log

# 查看/设置日志级别
log.get_log_level()       # 默认 "INFO"
log.set_log_level("DEBUG")

# 各级别输出
log.debug("调试信息")      # 灰色，级别低于当前设置时不输出
log.info("普通信息")       # 绿色
log.warn("警告信息")       # 黄色
log.error("错误信息")      # 红色
log.usage("用法说明")      # 蓝色，始终输出，不受 LOG_LEVEL 限制
```

---

## 3. base.pip - 包安装工具

按优先级依次尝试多个 PyPI 镜像站点安装 Python 包，国内网络环境下自动切换镜像源，提高安装成功率。

默认镜像优先级：清华 > 阿里云 > 中科大 > PyPI 官方。

```python
from baibao.base import pip

# 安装单个包
success, msg = pip.install("requests")
print(success, msg)  # True, 安装信息

# 安装指定版本
success, msg = pip.install("requests==2.31.0")

# 批量安装
results = pip.install(["numpy", "pandas", "matplotlib"])
# results: [(True, "..."), (True, "..."), (True, "...")]

# 自定义镜像源和超时时间
success, msg = pip.install(
    "requests",
    mirrors=["https://pypi.tuna.tsinghua.edu.cn/simple/"],
    timeout=60
)

# 修改 Python 命令路径
pip.set_python_command("python3")
pip.get_python_command()
```

---

## 4. db - 数据库

支持 MySQL 和 PostgreSQL，数据库驱动（pymysql / psycopg2）在首次使用时自动安装。

> 完整文档请参考 [SQL 数据库操作模块](db_sql.md)

```python
from baibao import sql, DbCfg, DbClient
# 或者通过子模块导入
# from baibao.db import sql, DbCfg, DbClient

# 1. 配置并注册数据源
cfg = DbCfg(host="localhost", port=3306, username="root",
            password="123456", database="test_db")
sql.set_client("default", cfg)

# 2. 执行写操作
sql.exec("INSERT INTO users (name, email) VALUES (%s, %s)",
         params=("张三", "zhangsan@example.com"))

# 3. 执行查询
users = sql.query("SELECT * FROM users WHERE name = %s", params=("张三",))
```

---

## 5. message.email - 邮件发送

支持纯文本、HTML 和带附件的邮件发送，支持抄送、密送和群发。自动判断 SSL / STARTTLS 加密方式。

### 5.1 基本配置

```python
from baibao.message.email import EmailClient, EmailCfg

config = EmailCfg(
    send_server="smtp.qq.com",
    send_port=465,
    username="your_email@qq.com",
    password="your_auth_code",
    sender_name="我的邮箱"
)

# 从 JSON 文件加载
config = EmailCfg.load_from_json_cfg("email_config.json")
```

### 5.2 发送纯文本邮件

```python
client = EmailClient(config)

result = client.send(
    to="recipient@example.com",
    subject="测试邮件",
    content="这是一封测试邮件"
)
print(result.message_id)       # 邮件 Message-ID
print(result.failed_recipients) # 空字典表示全部成功
```

### 5.3 发送 HTML 邮件

```python
html = """
<html>
<body>
    <h1>欢迎</h1>
    <p>这是一封 <strong>HTML</strong> 格式的邮件。</p>
</body>
</html>
"""

client.send(
    to="recipient@example.com",
    subject="HTML 邮件",
    content=html,
    is_html=True
)
```

### 5.4 发送带附件的邮件

```python
client.send(
    to="recipient@example.com",
    subject="带附件的邮件",
    content="请查看附件",
    attachments=["report.pdf", "data.xlsx"]
)
```

### 5.5 群发（含抄送、密送）

```python
client.send(
    to=["user1@example.com", "user2@example.com"],
    subject="群发邮件",
    content="Hello Everyone!",
    cc="manager@example.com",
    bcc=["admin1@example.com", "admin2@example.com"]
)
```

---

## 6. util.ocr - OCR 文字识别

支持 EasyOCR 和 PaddleOCR 两种引擎，提供统一的识别接口。相关依赖需额外安装：

```bash
python -m pip install ".[easyocr]"
python -m pip install ".[paddleocr]"
```

### 6.1 基本识别

```python
from baibao.util.ocr import EasyOcr, PaddleOcr

# 使用 EasyOCR
ocr = EasyOcr()
text = ocr.recognize("screenshot.png")
print(text)

# 使用 PaddleOCR
ocr = PaddleOcr()
text = ocr.recognize("screenshot.png")
```

### 6.2 详细识别（含位置和置信度）

```python
details = ocr.recognize_with_details("screenshot.png")
for item in details:
    print(f"文字: {item.text}")
    print(f"置信度: {item.confidence:.2f}")
    print(f"位置: {item.bbox}")  # [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
```

### 6.3 识别并绘制边界框

```python
# 返回绘制了边界框的图像数组，同时保存到文件
result_img = ocr.recognize_and_draw(
    "screenshot.png",
    output_path="result.png",
    color=(0, 255, 0),  # BGR 绿色
    thickness=2
)
```

### 6.4 OCR 管理器（运行时切换引擎）

```python
from baibao.util.ocr import OcrMgr, EasyOcr, PaddleOcr

mgr = OcrMgr(EasyOcr())
text = mgr.recognize("image.png")

# 切换到 PaddleOCR
mgr.set_strategy(PaddleOcr())
text = mgr.recognize("image.png")
```
