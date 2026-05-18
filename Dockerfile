FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建静态文件目录
RUN mkdir -p static/tiles

EXPOSE 8000

# 启动
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
