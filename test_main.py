import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app, celery_app
from constants import TASK_ANALYZE_SENTIMENT

client = TestClient(app)

@pytest.fixture
def mock_redis():
    """Mock thread-safe del cliente Redis en el backend de Celery."""
    mock = MagicMock()
    with patch.object(type(celery_app.backend), "client", new_callable=lambda: mock):
        yield mock

@patch("main.celery_app.send_task")
def test_predict_success(mock_send_task, mock_redis):
    mock_task = MagicMock()
    mock_task.id = "fake-task-id-123"
    mock_send_task.return_value = mock_task

    response = client.post("/predict", json={"text": "This is great!"})
    assert response.status_code == 202
    assert response.headers["location"] == "/result/fake-task-id-123"
    data = response.json()
    assert data["task_id"] == "fake-task-id-123"
    assert data["status"] == "Processing"
    mock_send_task.assert_called_once_with(TASK_ANALYZE_SENTIMENT, args=["This is great!"])
    mock_redis.set.assert_called_once_with("task_registry:fake-task-id-123", "QUEUED", ex=86400)

def test_predict_invalid_input_null():
    # Enviamos un payload que no cumple con el tipo str
    response = client.post("/predict", json={"text": None})
    assert response.status_code == 422

def test_predict_invalid_input_empty():
    # Enviamos texto vacío violando min_length=1
    response = client.post("/predict", json={"text": ""})
    assert response.status_code == 422

def test_predict_invalid_input_too_long():
    # Enviamos texto que supera los 1000 caracteres
    long_text = "a" * 1001
    response = client.post("/predict", json={"text": long_text})
    assert response.status_code == 422

@patch("main.AsyncResult")
def test_get_result_pending(mock_async_result, mock_redis):
    mock_task = MagicMock()
    mock_task.state = "PENDING"
    mock_async_result.return_value = mock_task
    mock_redis.exists.return_value = 1  # Tarea registrada y aún en cola

    response = client.get("/result/fake-task-id-123")
    assert response.status_code == 200
    assert response.json() == {"status": "Processing"}
    mock_redis.exists.assert_called_once_with("task_registry:fake-task-id-123")

@patch("main.AsyncResult")
def test_get_result_not_found(mock_async_result, mock_redis):
    mock_task = MagicMock()
    mock_task.state = "PENDING"
    mock_async_result.return_value = mock_task
    mock_redis.exists.return_value = 0  # Tarea nunca fue encolada

    response = client.get("/result/fake-task-id-123")
    assert response.status_code == 404
    assert response.json() == {"detail": "Task fake-task-id-123 not found"}
    mock_redis.exists.assert_called_once_with("task_registry:fake-task-id-123")

@patch("main.AsyncResult")
def test_get_result_success(mock_async_result):
    mock_task = MagicMock()
    mock_task.state = "SUCCESS"
    mock_task.result = {
        "text": "This is great!",
        "label": "POSITIVE",
        "score": 0.9998,
        "is_positive": True
    }
    mock_async_result.return_value = mock_task

    response = client.get("/result/fake-task-id-123")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Completed"
    assert data["result"]["is_positive"] is True
    assert data["result"]["score"] == 0.9998

@patch("main.AsyncResult")
def test_get_result_failure(mock_async_result):
    mock_task = MagicMock()
    mock_task.state = "FAILURE"
    mock_task.info = "Model inference timed out"
    mock_async_result.return_value = mock_task

    response = client.get("/result/fake-task-id-123")
    assert response.status_code == 200
    assert response.json() == {
        "status": "Failed",
        "error": "Model inference timed out"
    }

def test_health_check_healthy(mock_redis):
    mock_redis.ping.return_value = True
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "redis": "connected"}

def test_health_check_unhealthy(mock_redis):
    mock_redis.ping.side_effect = ConnectionError("Connection refused")
    response = client.get("/health")
    assert response.status_code == 503
    assert "Redis connection failed" in response.json()["detail"]
