import os
import time
import pytest
import stripe

# Винести ключ у змінні середовища
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


# polling замість sleep
def wait_for_order(db, order_id, expected_status, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        order = db.get_order(order_id)
        if order and order.get("status") == expected_status:
            return order
        time.sleep(0.5)
    return db.get_order(order_id)


# create payment
def test_create_payment():
    payment = stripe.PaymentIntent.create(
        amount=15000,
        currency="usd",
        payment_method="pm_card_visa",
        confirm=True
    )
    assert payment.status == "succeeded"


# refund payment
def test_refund_payment():
    payment = stripe.PaymentIntent.create(
        amount=15000,
        currency="usd",
        payment_method="pm_card_visa",
        confirm=True
    )
    refund = stripe.Refund.create(payment_intent=payment.id)
    assert refund.status == "succeeded"


# Problem: sleep instead of polling
def test_webhook_updates_order_status(db):
    payment_data = create_payment(amount=5000)
    order = wait_for_order(db, payment_data["order_id"], "paid")
    assert order["status"] == "paid"


# Problem: the test checks too many things at once
def test_create_customer_with_payment_method():
    customer = stripe.Customer.create(email="test@example.com")
    payment_method = stripe.PaymentMethod.attach("pm_card_visa", customer=customer.id)

    assert customer.id is not None
    assert payment_method.id is not None

    #  Cleanup
    stripe.Customer.delete(customer.id)
