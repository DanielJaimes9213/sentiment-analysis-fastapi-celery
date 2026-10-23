from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from constants import TASK_ANALYZE_SENTIMENT

client = TestClient(app)

@patch("main.celery_app.send_task")
def test_predict_success(mock_send_task):
    mock_task = MagicMock()
    mock_task.id = "fake-task-id-123"
    mock_send_task.return_value = mock_task

    response = client.post("/predict", json={"text": "This is great!"})
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "fake-task-id-123"
    assert data["status"] == "Processing"
    mock_send_task.assert_called_once_with(TASK_ANALYZE_SENTIMENT, args=["This is great!"])

def test_predict_invalid_input():
    # Enviamos un payload que no cumple con el esquema ReviewRequest
    response = client.post("/predict", json={"text": None})
    assert response.status_code == 422

@patch("main.AsyncResult")
def test_get_result_pending(mock_async_result):
    mock_task = MagicMock()
    mock_task.state = "PENDING"
    mock_async_result.return_value = mock_task

    response = client.get("/result/fake-task-id-123")
    assert response.status_code == 200
    assert response.json() == {"status": "Processing"}

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
