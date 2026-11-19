FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY . .
# Hugging Face Spaces expects 7860; Render/others pass $PORT.
ENV PORT=7860
EXPOSE 7860
CMD ["python", "app.py"]
