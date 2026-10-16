import pytest
import requests

# Базова адреса запущеного сервісу
BASE_URL = "http://localhost:3000/api"


# ==============================================================================
# 1. HAPPY PATH (Успішні сценарії)
# ==============================================================================

def test_successful_payment_creation():
    """1. Happy Path: Успішне створення та підтвердження платежу карткою."""
    payload = {
        "amount": 2000,  # $20.00 в центах
        "currency": "usd",
        "payment_method": "pm_card_visa",
        "confirm": True
    }
    response = requests.post(f"{BASE_URL}/payments", json=payload)

    assert response.status_code == 201, f"Очікувався статус 201, отримано {response.status_code}"
    data = response.json()
    assert data["status"] == "succeeded", f"Статус платіжки має бути succeeded, а не {data.get('status')}"
    assert "id" in data, "Відповідь не містить ідентифікатора транзакції (id)"


def test_successful_refund():
    """2. Happy Path: Успішне повернення коштів (Refund) для успішного платежу."""
    create_payload = {"amount": 1500, "currency": "usd", "payment_method": "pm_card_visa", "confirm": True}
    create_res = requests.post(f"{BASE_URL}/payments", json=create_payload)
    payment_id = create_res.json()["id"]
    refund_payload = {"amount": 1500}
    response = requests.post(f"{BASE_URL}/payments/{payment_id}/refund", json=refund_payload)

    assert response.status_code in [200, 201], f"Очікувався успішний статус, отримано {response.status_code}"
    data = response.json()
    assert data["status"] == "succeeded"


# ==============================================================================
# 2. ІДЕМПОТЕНТНІСТЬ (Idempotency)
# ==============================================================================

def test_payment_idempotency_key():
    """3. Ідемпотентність: Повторний запит з тим самим Idempotency-Key повертає той самий результат без дублювання списання."""
    headers = {
        "Idempotency-Key": "test-key-unique-uuid-12345",
        "Content-Type": "application/json"
    }
    payload = {
        "amount": 3000,
        "currency": "usd",
        "payment_method": "pm_card_visa",
        "confirm": True
    }

    res_first = requests.post(f"{BASE_URL}/payments", json=payload, headers=headers)
    assert res_first.status_code == 201, f"Очікувався статус 201, отримано {res_first.status_code}"
    data_first = res_first.json()

    res_second = requests.post(f"{BASE_URL}/payments", json=payload, headers=headers)
    assert res_second.status_code in [200, 201], f"Очікувався успішний статус, отримано {res_second.status_code}"
    data_second = res_second.json()

    assert data_first["id"] == data_second[
        "id"], "Ідемпотентність порушена: створено новий платіж замість повернення кешованого"


# ==============================================================================
# 3. НЕГАТИВНІ СЦЕНАРІЇ (Negative Scenarios)
# ==============================================================================

def test_payment_declined_card():
    """4. Негативний: Відхилена картка (insufficient funds або test card declined)."""
    payload = {
        "amount": 1000,
        "currency": "usd",
        "payment_method": "pm_card_declined",  # спеціальна тестова картка Stripe для decline
        "confirm": True
    }
    response = requests.post(f"{BASE_URL}/payments", json=payload)

    assert response.status_code in [400, 402], f"Очікувався код помилки платежу, отримано {response.status_code}"
    data = response.json()
    assert data.get("error") or data.get("status") == "failed", "Відповідь має містити опис помилки або статус failed"


def test_payment_invalid_currency():
    """5. Негативний: Передача непідтримуваної або невалідної валюти."""
    payload = {
        "amount": 1000,
        "currency": "INVALID",
        "payment_method": "pm_card_visa",
        "confirm": True
    }
    response = requests.post(f"{BASE_URL}/payments", json=payload)

    assert response.status_code == 400, "Сервер має повертати 400 Bad Request при невалідній валюті"


def test_refund_nonexistent_charge():
    """6. Негативний: Спроба повернути кошти для неіснуючого charge_id."""
    refund_payload = {
        "charge_id": "ch_fake_nonexistent_id_9999",
        "amount": 500
    }
    response = requests.post(f"{BASE_URL}/refunds", json=refund_payload)

    assert response.status_code in [404, 400], "Повернення для неіснуючого платежу повинно відхилятися"


# ==============================================================================
# 4. EDGE CASES (Граничні випадки)
# ==============================================================================

def test_edge_case_zero_amount():
    """7. Edge Case: Створення платежу з нульовою сумою (amount = 0)."""
    payload = {
        "amount": 0,
        "currency": "usd",
        "payment_method": "pm_card_visa",
        "confirm": True
    }
    response = requests.post(f"{BASE_URL}/payments", json=payload)

    assert response.status_code == 400, "Платіж із нульовою сумою має відхилятися валідацією (400)"


def test_edge_case_negative_amount():
    """8. Edge Case: Створення платежу з від'ємною сумою."""
    payload = {
        "amount": -500,
        "currency": "usd",
        "payment_method": "pm_card_visa",
        "confirm": True
    }
    response = requests.post(f"{BASE_URL}/payments", json=payload)

    assert response.status_code == 400, "Платіж з від'ємною сумою має блокуватися системою"


def test_edge_case_partial_refund_exceeding_total():
    """9. Edge Case: Спроба повернути суму, що перевищує початковий платіж."""
    create_payload = {"amount": 1000, "currency": "usd", "payment_method": "pm_card_visa", "confirm": True}
    create_res = requests.post(f"{BASE_URL}/payments", json=create_payload)
    payment_id = create_res.json()["id"]

    refund_payload = {
        "amount": 2000
    }
    response = requests.post(f"{BASE_URL}/payments/{payment_id}/refund", json=refund_payload)

    assert response.status_code in [400, 422], f"Система не повинна дозволяти повертати суму більшу, ніж сума оригінального платежу. Отримано статус: {response.status_code}"


def test_edge_case_missing_required_fields():
    """10. Edge Case: Відправка порожнього або неповного JSON-об'єкта."""
    payload = {}
    response = requests.post(f"{BASE_URL}/payments", json=payload)

    assert response.status_code == 400, "Запит без обов'язкових полів повинен повернути помилку валідації 400"