FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
RUN useradd -m enk && mkdir /data && chown enk /data
USER enk
ENV ENK_DATA_DIR=/data
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
