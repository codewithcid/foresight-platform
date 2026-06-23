"""A small synthetic policy knowledge base. Support replies are grounded in
this -- the AI is told which policy applies and the exact text, rather than
inventing terms, which is the actual point being demonstrated ("reply
according to terms and conditions").
"""
from __future__ import annotations

POLICIES = {
    "returns": {
        "title": "Returns",
        "text": ("Items can be returned within 7 days of delivery if unworn, unwashed, and with tags "
                 "attached. Refunds are processed to the original payment method within 5-7 business "
                 "days of the item being received back at our warehouse."),
    },
    "exchange": {
        "title": "Size Exchange",
        "text": ("Free size exchange is available within 10 days of delivery, subject to stock "
                 "availability. If the requested size is out of stock, a full refund is offered instead."),
    },
    "damaged_item": {
        "title": "Damaged or Defective Items",
        "text": ("Damaged or defective items are replaced free of cost or fully refunded, no questions "
                  "asked, provided it's reported within 48 hours of delivery with a photo of the issue."),
    },
    "shipping_delay": {
        "title": "Shipping Delays",
        "text": ("Standard delivery takes 4-6 business days. Orders delayed beyond 10 business days are "
                  "eligible for a coupon credit of 10% of order value, or a full refund if the customer "
                  "no longer wants the item."),
    },
    "cod_refund": {
        "title": "Cash on Delivery Refunds",
        "text": ("Refunds on Cash-on-Delivery orders are issued as store credit instantly, or as a bank "
                  "transfer within 7 business days if the customer prefers cash back."),
    },
    "cancellation": {
        "title": "Order Cancellation",
        "text": ("Orders can be cancelled free of charge any time before they ship. Once shipped, the "
                  "order falls under the standard Returns policy instead."),
    },
}


def match_policy(case_type: str) -> dict | None:
    mapping = {
        "refund_request": "returns",
        "complaint": "damaged_item",
        "shipping_question": "shipping_delay",
        "exchange_request": "exchange",
        "cancellation": "cancellation",
        "policy_question": "returns",
    }
    key = mapping.get(case_type)
    return {"key": key, **POLICIES[key]} if key else None
