FROM python:3.11-slim
WORKDIR /app
COPY analytics.py .
EXPOSE 8082
CMD ["python3", "analytics.py"]
