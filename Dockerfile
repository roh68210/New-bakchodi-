FROM python:3.10-slim

WORKDIR /app

RUN apt update && apt install -y ffmpeg aria2 wget && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
