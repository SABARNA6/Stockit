
FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir \
    https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl
# RUN python -m spacy download en_core_web_sm
COPY . .
RUN mkdir -p data/output
ENV PORT=10000
EXPOSE 10000
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 300 "api.routes:app"