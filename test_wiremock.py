import time
import pytest
import requests

BASE_URL = "http://localhost:8080"


# Тест 1: Успішна транзакція (200 OK)
def test_successful_payment_intent():
    url = f"{BASE_URL}/v1/payment_intents"
    response = requests.post(url)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "pi_mock_001"
    assert data["status"] == "requires_capture"
    assert data["amount"] == 15000
    assert data["currency"] == "usd"


# Тест 2: Відмова картки (402 Payment Required)
def test_card_declined():
    url = f"{BASE_URL}/v1/payment_intents/declined"
    response = requests.post(url)

    assert response.status_code == 402
    data = response.json()
    assert data["error"]["code"] == "card_declined"
    assert data["error"]["decline_code"] == "insufficient_funds"
    assert data["error"]["message"] == "Your card has insufficient funds."


# Тест 3: Помилка сервера (503 Service Unavailable)
def test_server_error():
    url = f"{BASE_URL}/v1/payment_intents/error"
    response = requests.post(url)

    assert response.status_code == 503
    data = response.json()
    assert data["error"]["type"] == "api_error"
    assert data["error"]["message"] == "Service unavailable"


# Тест 4: Таймаут відповіді (10 секунд)
def test_payment_timeout():
    url = f"{BASE_URL}/v1/payment_intents/timeout"
    start_time = time.time()
    response = requests.post(url)
    duration = time.time() - start_time

    assert response.status_code == 200
    assert response.json()["id"] == "pi_mock_timeout"
    assert duration >= 10.0  # Перевіряємо, що затримка дійсно була не менше 10 секунд