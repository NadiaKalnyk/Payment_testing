import pytest
import jsonschema
from jsonschema import validate

# 1. JSON Schema для Stripe webhook payload payment_intent.succeeded
WEBHOOK_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Stripe Webhook Event — payment_intent.succeeded",
    "type": "object",
    "required": ["id", "type", "created", "data"],
    "properties": {
        "id": {
            "type": "string",
            "pattern": "^evt_"
        },
        "type": {
            "type": "string",
            "const": "payment_intent.succeeded"
        },
        "created": {
            "type": "number"
        },
        "data": {
            "type": "object",
            "required": ["object"],
            "properties": {
                "object": {
                    "type": "object",
                    "required": ["id", "status", "amount", "currency"],
                    "properties": {
                        "id": {
                            "type": "string",
                            "pattern": "^pi_"
                        },
                        "status": {
                            "type": "string"
                        },
                        "amount": {
                            "type": "number"
                        },
                        "currency": {
                            "type": "string"
                        }
                    }
                }
            }
        }
    }
}


@pytest.fixture
def valid_payload():
    return {
        "id": "evt_3Py5dN2eZvKYlo1234567890",
        "type": "payment_intent.succeeded",
        "created": 1710751524,
        "data": {
            "object": {
                "id": "pi_3Py5dN2eZvKYlo",
                "status": "succeeded",
                "amount": 15600,
                "currency": "usd"
            }
        }
    }


# Тест 1: валідний payload → schema valid
def test_webhook_schema_valid_payload(valid_payload):
    try:
        validate(instance=valid_payload, schema=WEBHOOK_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        pytest.fail(f"Валідний payload не пройшов перевірку схеми: {e.message}")


# Тест 2: payload без required поля (напр. data.object.status) → schema invalid
def test_webhook_schema_missing_required_field(valid_payload):
    del valid_payload["data"]["object"]["status"]

    with pytest.raises(jsonschema.exceptions.ValidationError) as exc_info:
        validate(instance=valid_payload, schema=WEBHOOK_SCHEMA)

    assert "'status' is a required property" in exc_info.value.message


# Тест 3: payload з неправильним типом (amount: string замість number) → schema invalid
def test_webhook_schema_invalid_field_type(valid_payload):
    valid_payload["data"]["object"]["amount"] = "15600"

    with pytest.raises(jsonschema.exceptions.ValidationError) as exc_info:
        validate(instance=valid_payload, schema=WEBHOOK_SCHEMA)

    assert "'15600' is not of type 'number'" in exc_info.value.message