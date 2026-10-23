import os
from celery import Celery
from transformers import pipeline
from constants import TASK_ANALYZE_SENTIMENT

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

celery_app = Celery(
    "sentiment_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Cargamos el pipeline una sola vez al inicializar el worker
classifier = pipeline("sentiment-analysis", model="distilbert/distilbert-base-uncased-finetuned-sst-2-english")

@celery_app.task(name=TASK_ANALYZE_SENTIMENT)
def analyze_sentiment_task(text: str):
    result = classifier(text)[0]
    return {
        "text": text,
        "label": result["label"],
        "score": float(result["score"]),
        "is_positive": result["label"] == "POSITIVE"
    }
    