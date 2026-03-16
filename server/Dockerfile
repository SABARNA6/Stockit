FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DEFAULT_TIMEOUT=180

COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
	&& pip install --prefer-binary --retries 8 --timeout 180 -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["python", "app.py"]
