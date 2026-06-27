FROM python:3.12-slim

WORKDIR /app

COPY backend/ .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["uvicorn", "tracking_server:app", "--host", "0.0.0.0", "--port", "8080"]