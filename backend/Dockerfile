FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（exiftool 用于 EXIF 读取）
# ffmpeg 用 imageio-ffmpeg Python 包提供静态二进制，避免 apt 下载大依赖
ENV DEBIAN_FRONTEND=noninteractive TZ=UTC
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libimage-exiftool-perl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
