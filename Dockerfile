FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

RUN mkdir -p uploads outputs

EXPOSE 8080

CMD ["gunicorn", "app:app", "--workers", "2", "--timeout", "120", "--bind", "0.0.0.0:8080"]
