import os
from fastapi import FastAPI, Response, status
from pydantic import BaseModel, Field
from celery import Celery
from celery.result import AsyncResult
from constants import TASK_ANALYZE_SENTIMENT

# Configuración de Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Instancia del cliente Celery
celery_app = Celery(
    "sentiment_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

app = FastAPI(title="Sentiment Analysis API")

class ReviewRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Texto de la reseña a analizar (entre 1 y 1000 caracteres)"
    )

@app.post("/predict", status_code=status.HTTP_202_ACCEPTED)
def predict(request: ReviewRequest, response: Response):
    # Encolamos la tarea en Redis pasando el nombre registrado del worker
    task = celery_app.send_task(TASK_ANALYZE_SENTIMENT, args=[request.text])
    
    # Cabecera estándar REST para Request-Reply asíncrono
    response.headers["Location"] = f"/result/{task.id}"
    
    # Respondemos al cliente con el ID para monitorear el progreso
    return {"task_id": task.id, "status": "Processing"}

@app.get("/result/{task_id}")
def get_result(task_id: str):
  # Consultamos el estado de la tarea en el Backend de Celery
    task = AsyncResult(task_id, app=celery_app)
    
    if task.state == "PENDING":
        return {"status": "Processing"}
    elif task.state == "SUCCESS":
        return {"status": "Completed","result": task.result}
    elif task.state == "FAILURE":
        return {"status": "Failed", "error": str(task.info)}    
    return {"status": task.state}

