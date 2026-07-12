# AI 模块

> 本文档介绍 `baibao.ai` 模块的使用方法，包含 LLM 大语言模型和 OCR 文字识别两大子模块。

## 模块概述

`baibao.ai` 模块提供统一的 AI 能力接口，采用策略模式设计，支持运行时自由切换后端实现：

| 子模块 | 功能 | 说明 |
|--------|------|------|
| `baibao.ai.llm` | 大语言模型 | 支持单轮/多轮对话、流式输出，兼容 OpenAI API 格式 |
| `baibao.ai.ocr` | 文字识别 | 支持 EasyOCR、PaddleOCR，提供文本识别和可视化绘制 |

---

## LLM 子模块

### 基本使用

```python
from baibao.ai.llm import chat, set_llm_service
from baibao.ai.llm.openai_llm import OpenAiLlm

# 1. 设置 LLM 服务
set_llm_service("default", OpenAiLlm(
    api_key="sk-xxx",
    base_url="https://api.openai.com/v1",
    model="gpt-4o-mini",
))

# 2. 单轮对话
response = chat("你好，请介绍一下自己")
print(response.content)
```

### 支持的服务商

`OpenAiLlm` 兼容所有 OpenAI API 格式的服务商：

```python
# OpenAI 官方
llm = OpenAiLlm(api_key="sk-xxx")

# DeepSeek
llm = OpenAiLlm(
    api_key="sk-xxx",
    base_url="https://api.deepseek.com/v1",
    model="deepseek-chat",
)

# 月之暗面 (Moonshot)
llm = OpenAiLlm(
    api_key="sk-xxx",
    base_url="https://api.moonshot.cn/v1",
    model="moonshot-v1-8k",
)

# 智谱 AI (GLM)
llm = OpenAiLlm(
    api_key="xxx",
    base_url="https://open.bigmodel.cn/api/paas/v4",
    model="glm-4",
)

# 本地 Ollama
llm = OpenAiLlm(
    api_key="ollama",
    base_url="http://localhost:11434/v1",
    model="llama3",
)
```

### 环境变量配置

支持通过环境变量自动获取配置，无需硬编码：

```bash
# 设置环境变量
export OPENAI_API_KEY="sk-xxx"
export OPENAI_BASE_URL="https://api.openai.com/v1"

# 或使用 DeepSeek 的环境变量
export DEEPSEEK_API_KEY="sk-xxx"
```

```python
# 自动从环境变量读取
llm = OpenAiLlm()  # 使用默认模型 gpt-4o-mini
```

### 多配置管理

可以设置多个 LLM 配置，按需切换：

```python
from baibao.ai.llm import chat, set_llm_service
from baibao.ai.llm.openai_llm import OpenAiLlm

# 设置多个配置
set_llm_service("fast", OpenAiLlm(model="gpt-4o-mini"))
set_llm_service("code", OpenAiLlm(model="gpt-4o"))

# 使用指定配置
response = chat("写一个快排算法", llm_name="code")
response = chat("简要概括", llm_name="fast")
```

### 多轮对话

```python
from baibao.ai.llm import chat_with_history, LlmMessage

messages = [
    LlmMessage(role="system", content="你是一个有用的助手"),
    LlmMessage(role="user", content="你好"),
    LlmMessage(role="assistant", content="你好！有什么可以帮助你的吗？"),
    LlmMessage(role="user", content="今天天气怎么样？"),
]

response = chat_with_history(messages)
print(response.content)
```

### 流式输出

```python
from baibao.ai.llm import stream_chat

# 逐步输出，适合长文本生成
for chunk in stream_chat("讲一个关于人工智能的故事"):
    print(chunk, end="", flush=True)
```

### 响应对象

`LlmResponse` 包含丰富的元数据：

```python
from baibao.ai.llm import chat

response = chat("你好")

print(response.content)        # 响应文本
print(response.model)          # 使用的模型名称
print(response.usage)          # token 使用情况
# {'prompt_tokens': 10, 'completion_tokens': 20, 'total_tokens': 30}
print(response.finish_reason)  # 结束原因: 'stop'、'length' 等
```

### API 参数

对话方法支持多种参数控制生成行为：

```python
response = chat(
    prompt="写一首诗",
    system="你是一个诗人",
    temperature=0.9,    # 温度，越高越随机 (0~2)
    max_tokens=500,     # 最大生成 token 数
    top_p=0.9,          # 核采样参数
    frequency_penalty=0.5,  # 频率惩罚
)
```

### 管理函数

```python
from baibao.ai.llm import get_llm_service, set_llm_service, remove_llm_service

# 设置服务
set_llm_service("my_llm", OpenAiLlm(api_key="sk-xxx"))

# 获取服务
llm = get_llm_service("my_llm")

# 移除服务
remove_llm_service("my_llm")
```

---

## OCR 子模块

### 基本使用

```python
from baibao.ai.ocr import recognize

# 识别图片文字（默认使用 EasyOCR）
text = recognize("invoice.png")
print(text)
```

### 支持的 OCR 引擎

| 引擎 | 类名 | 特点 |
|------|------|------|
| EasyOCR | `EasyOcr` | 基于 PyTorch，支持 80+ 语言，支持 GPU 加速 |
| PaddleOCR | `PaddleOcr` | 百度飞桨，高精度，内置角度分类器 |

### 切换 OCR 引擎

```python
from baibao.ai.ocr import recognize, set_ocr_service
from baibao.ai.ocr.paddle_ocr import PaddleOcr

# 切换为 PaddleOCR
set_ocr_service("paddle", PaddleOcr(lang='ch'))

# 使用指定引擎
text = recognize("image.png", ocr_name="paddle")
```

### EasyOCR 配置

```python
from baibao.ai.ocr.easy_ocr import EasyOcr

# 默认配置（中文 + 英文）
ocr = EasyOcr()

# 多语言配置
ocr = EasyOcr(langs=['ch_sim', 'en', 'ja', 'ko'])

# 启用 GPU 加速
ocr = EasyOcr(gpu=True)

# 指定模型存储目录
ocr = EasyOcr(model_storage_directory="/path/to/models")
```

### PaddleOCR 配置

```python
from baibao.ai.ocr.paddle_ocr import PaddleOcr

# 默认配置（中英文）
ocr = PaddleOcr()

# 禁用角度分类器（更快）
ocr = PaddleOcr(use_angle_cls=False)

# 英文识别
ocr = PaddleOcr(lang='en')
```

### 详细识别结果

获取文字位置和置信度：

```python
from baibao.ai.ocr import recognize_with_details

results = recognize_with_details("image.png")

for item in results:
    print(f"文本: {item.text}")
    print(f"位置: {item.bbox}")      # [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
    print(f"置信度: {item.confidence:.2f}")
    print("---")
```

### 可视化绘制

在图片上绘制识别结果：

```python
from baibao.ai.ocr import recognize_and_draw

# 识别并绘制边界框，保存结果图
img = recognize_and_draw(
    "image.png",
    output_path="result.png",     # 保存路径
    color=(0, 255, 0),            # 绿色边界框
    thickness=2,                  # 线条粗细
)
```

### 使用 OpenCV 图像数组

支持直接传入 OpenCV 图像数组：

```python
import cv2
from baibao.ai.ocr import recognize

# 读取图片
img = cv2.imread("image.png")

# 直接传入图像数组
text = recognize(img)
```

### OCR 管理函数

```python
from baibao.ai.ocr import get_ocr_service, set_ocr_service, remove_ocr_service

# 设置服务
set_ocr_service("my_ocr", PaddleOcr())

# 获取服务
ocr = get_ocr_service("my_ocr")

# 移除服务
remove_ocr_service("my_ocr")
```

---

## 依赖说明

### LLM 子模块

| 依赖包 | 说明 | 安装方式 |
|--------|------|----------|
| openai | OpenAI 官方 SDK | 首次使用自动安装 |

### OCR 子模块

| 依赖包 | 说明 | 安装方式 |
|--------|------|----------|
| easyocr | EasyOCR 引擎 | 首次使用自动安装 |
| opencv-python | 图像处理 | easyocr 依赖 |
| paddleocr | PaddleOCR 引擎 | 需手动安装: `pip install paddleocr` |

---

## 完整示例

### LLM 多服务商切换

```python
from baibao.ai.llm import chat, set_llm_service
from baibao.ai.llm.openai_llm import OpenAiLlm

# 配置多个服务商
set_llm_service("gpt", OpenAiLlm(
    api_key="sk-xxx",
    model="gpt-4o",
))

set_llm_service("deepseek", OpenAiLlm(
    api_key="sk-xxx",
    base_url="https://api.deepseek.com/v1",
    model="deepseek-chat",
))

# 按需切换
response1 = chat("你好", llm_name="gpt")
response2 = translate("你好", llm_name="deepseek")
```

### OCR 批量识别

```python
import os
from baibao.ai.ocr import recognize

# 批量识别目录下的图片
image_dir = "./images"
for filename in os.listdir(image_dir):
    if filename.endswith(('.png', '.jpg', '.jpeg')):
        path = os.path.join(image_dir, filename)
        text = recognize(path)
        print(f"{filename}: {text}")
```

### OCR 结果筛选高置信度

```python
from baibao.ai.ocr import recognize_with_details

results = recognize_with_details("image.png")

# 只保留置信度大于 0.8 的结果
high_confidence = [r for r in results if r.confidence > 0.8]

for item in high_confidence:
    print(f"{item.text} ({item.confidence:.1%})")
```
