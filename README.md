# Sentiment Analysis API (FastAPI + Celery + Redis + Transformers)

Microservicio de análisis de sentimiento para reseñas de texto implementado bajo el patrón arquitectónico **Asynchronous Request-Reply (Polling)**.

El sistema desacopla la recepción HTTP de la inferencia pesada de Machine Learning mediante una cola de tareas en segundo plano.

---

## 🏛️ Arquitectura

```
[Cliente] 
   │ 1. POST /predict {"text": "..."}
   ▼
[API: FastAPI] (main.py) ──2. Encola tarea (.send_task)──► [Broker/Backend: Redis]
   │                                                             │
   │ 3. Devuelve {"task_id": "...", "status": "Processing"}      │ 4. Consume tarea
   ▼                                                             ▼
[Cliente]                                               [Worker: Celery] (tasks.py)
   │                                                             │ 5. Inferencia DistilBERT
   │ 6. GET /result/{task_id} (Polling)                          │ 6. Guarda resultado
   ▼                                                             ▼
[API: FastAPI] ◄─────────7. Consulta AsyncResult───────── [Broker/Backend: Redis]
```

### Decisiones de Diseño Clave
* **Desacoplamiento de Procesos:** La API de FastAPI no importa librerías pesadas (`torch`, `transformers`) ni carga modelos en memoria en su arranque. Encola las tareas invocando `celery_app.send_task(...)` mediante constantes compartidas en `constants.py`.
* **Inferencia Aislada:** El worker de Celery aloja el pipeline de Hugging Face (`distilbert/distilbert-base-uncased-finetuned-sst-2-english`), ejecutando el cómputo en un proceso independiente.

---

## 🚀 Puesta en Marcha con Docker Compose

La forma recomendada de ejecutar el proyecto completo es mediante Docker Compose:

```bash
docker-compose up --build
```

Esto levantará 3 servicios:
* `redis`: Broker de mensajes y backend de resultados (puerto `6379`).
* `api`: Servidor web FastAPI / Uvicorn (puerto `8000`).
* `worker`: Worker de Celery ejecutando inferencia con DistilBERT.

---

## 📡 Endpoints de la API

### 1. Encolar Análisis
* **Método:** `POST`
* **Ruta:** `/predict`
* **Body:**
  ```json
  {
    "text": "The battery life on this laptop is incredible!"
  }
  ```
* **Respuesta (`202 Accepted`):**
  * **Headers:** `Location: /result/{task_id}`
  ```json
  {
    "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "status": "Processing"
  }
  ```

---

### 2. Consultar Resultado
* **Método:** `GET`
* **Ruta:** `/result/{task_id}`
* **Respuesta en progreso:**
  ```json
  {
    "status": "Processing"
  }
  ```
* **Respuesta completada:**
  ```json
  {
    "status": "Completed",
    "result": {
      "text": "The battery life on this laptop is incredible!",
      "label": "POSITIVE",
      "score": 0.9998,
      "is_positive": true
    }
  }
* **Respuesta de tarea no encontrada (`404 Not Found`):**
  ```json
  {
    "detail": "Task 9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d not found"
  }
  ```

---

### 3. Consultar Salud del Servicio (Healthcheck)
* **Método:** `GET`
* **Ruta:** `/health`
* **Respuesta (`200 OK`):**
  ```json
  {
    "status": "healthy",
    "redis": "connected"
  }
  ```
* **Respuesta en fallo de infraestructura (`503 Service Unavailable`):**
  ```json
  {
    "detail": "Redis connection failed: Connection refused"
  }
  ```

---

## 🧪 Pruebas Unitarias

La suite de pruebas en `test_main.py` está completamente aislada usando `unittest.mock.patch` para simular la interacción con Celery y Redis, ejecutándose en menos de un segundo:

```bash
# Ejecutar suite de pruebas
pytest test_main.py
```
