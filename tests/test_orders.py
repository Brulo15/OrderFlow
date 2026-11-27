from datetime import datetime, timedelta

import pytest
import orders

from orders import (
    calculate_order_total,
    find_order_by_id,
    get_next_order_id,
    load_orders,
    can_cancel_order,
)


def test_finds_existing_order():
    orders_list = load_orders()

    order = find_order_by_id(orders_list, "ORD-0001")

    assert order is not None
    assert order["customer_id"] == "CUS-001"


def test_returns_none_for_unknown_order():
    orders_list = load_orders()

    order = find_order_by_id(orders_list, "ORD-9999")

    assert order is None


def test_calculates_total_from_items():
    items = [
        {"product_id": "PRD-001", "quantity": 2, "unit_price": 10.50},
        {"product_id": "PRD-002", "quantity": 1, "unit_price": 5.25},
    ]

    assert calculate_order_total(items) == 26.25


def test_generates_next_order_id():
    orders_list = [{"id": "ORD-0003"}, {"id": "ORD-0011"}]

    assert get_next_order_id(orders_list) == "ORD-0012"


@pytest.mark.parametrize(
    "status,limit_minutes,extra_seconds,expected",
    [
        ("PROCESSING", 15, 0, True),
        ("PROCESSING", 15, 1, False),
        ("PAID", 30, 0, True),
        ("PAID", 30, 1, False),
    ],
)
def test_cancellation_time_limits(
    monkeypatch, status, limit_minutes, extra_seconds, expected
):
    created_at = datetime(2026, 11, 27, 12, 0, 0)
    current_time = created_at + timedelta(
        minutes=limit_minutes,
        seconds=extra_seconds,
    )

    order = {
        "id": "ORD-TEST",
        "status": status,
        "created_at": created_at.isoformat(),
    }

    monkeypatch.setattr(
        orders,
        "get_current_datetime",
        lambda: current_time,
    )

    can_cancel, message = can_cancel_order(order)

    assert can_cancel is expected

@pytest.mark.parametrize(
    "status",
    ["SHIPPED", "DELIVERED", "CANCELLED"],
)
def test_cannot_cancel_orders_with_final_statuses(status):
    order = {
        "id": "ORD-TEST",
        "status": status,
        "created_at": datetime(2026, 11, 27, 12, 0, 0).isoformat(),
    }

    can_cancel, message = can_cancel_order(order)

    assert can_cancel is False
    assert "statusie" in message

def test_cancel_order_changes_only_status(monkeypatch):
    order = {
        "id": "ORD-TEST",
        "status": "NEW",
        "customer_id": "CUS-001",
        "payment_method": "CARD",
        "created_at": "2026-11-27T12:00:00",
        "items": [{"product_id": "PRD-001", "quantity": 2}],
        "total": 100.0,
    }

    original_order = order.copy()
    orders_list = [order]

    monkeypatch.setattr(orders, "save_orders", lambda orders_list: None)

    success, message = orders.cancel_order(orders_list, order)

    assert success is True
    assert order["status"] == "CANCELLED"

    original_order["status"] = "CANCELLED"
    assert order == original_order