FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libmupdf-dev \
    mupdf-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# app/main.py인 경우
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]