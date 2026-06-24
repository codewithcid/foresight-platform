# Foresight — Store Integration Guide

Connect any shopping site to Foresight's **abandoned-cart recovery agent**. Your store
reports cart events; Foresight detects abandonment, issues a budget-safe discount,
WhatsApps the customer a deep link back to their cart, and proves whether the push
actually recovered the sale — escalating the offer only if it pays off.

```
Store ──cart events──▶ Foresight ──WhatsApp + discount──▶ Customer ──back to cart──▶ Store
        purchase  ─────────────────▶ attribution + proof (predicted vs. actual)
```

## 1. Credentials
From the Foresight app → **Cart Recovery → Connect your store**:
- **Base URL** — e.g. `https://foresight-kp1g.onrender.com`
- **Ingest key** — sent as header `X-Foresight-Key` on every event
- **Store cart URL template** — set this in Foresight to your cart page, e.g.
  `https://your-store.com/cart/{cart_id}` (`{cart_id}` is substituted per customer)

## 2. Send cart events  →  `POST {BASE}/api/store/event`
Headers: `Content-Type: application/json`, `X-Foresight-Key: <key>`

```json
{
  "type": "cart_updated | cart_abandoned | purchase",
  "cart_id": "stable-id-per-cart-session",
  "customer": { "id": "u_9", "name": "Asha", "phone": "+9162...", "email": "a@x.com" },
  "items": [{ "name": "Kurta", "qty": 1, "price": 1299 }],
  "value": 1299,
  "currency": "INR",
  "discount_code": "BACK10-7F3A"
}
```

| Event | When to send | Notes |
|---|---|---|
| `cart_updated` | items added/removed, or user idle on cart | include `customer.phone` (E.164) if known |
| `cart_abandoned` | *(optional)* tab close / explicit | fires recovery immediately; otherwise Foresight's timer does |
| `purchase` | checkout success | include final `value` + `discount_code` if one was applied |

**Responses** — cart events: `{ "ok": true, "status": "active|abandoned" }` ·
purchase: `{ "ok": true, "attributed": true, "recovered": true, "run_id": 42 }`

> If you don't send `cart_abandoned`, Foresight marks a cart abandoned after a
> configurable window (default 120s) of no purchase and acts on its own.

## 3. Apply Foresight discount codes
Customers arrive from the WhatsApp push at `…/cart/{cart_id}?fs_code=BACK10-7F3A`.

1. Read `fs_code` from the query string.
2. Validate it: `GET {BASE}/api/discount/validate?code=BACK10-7F3A`
   → `{ "valid": true, "percent": 10, "cart_id": "...", "expires_at": 17... }`
3. If valid, apply `percent` off and show a banner ("🎉 Your 10% comeback offer is applied").
4. Pass the same code through in the `purchase` event so the recovery is attributed.

Your cart page **must** be reachable at `/cart/{cart_id}` and restore that cart, so a
returning customer lands back on their exact items.

## 4. Drop-in helper
```js
const FORESIGHT_BASE = "https://foresight-kp1g.onrender.com";
const FORESIGHT_KEY = "<your-ingest-key>";

export async function fsTrack(type, { cartId, customer, items, value, discountCode }) {
  try {
    await fetch(`${FORESIGHT_BASE}/api/store/event`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Foresight-Key": FORESIGHT_KEY },
      body: JSON.stringify({
        type, cart_id: cartId, customer, items, value, currency: "INR",
        ...(discountCode ? { discount_code: discountCode } : {}),
      }),
    });
  } catch (e) { console.warn("foresight track failed", e); }
}

// on cart change:   fsTrack("cart_updated", { cartId, customer, items, value })
// on checkout:      fsTrack("purchase",     { cartId, value, discountCode })
```

## Checklist
- [ ] `cart_id` is stable across the abandon → return journey
- [ ] `customer.phone` is E.164 (`+91…`) — required to send the push
- [ ] cart page handles `/cart/{cart_id}?fs_code=…` (validate + apply)
- [ ] `purchase` is sent only on real checkout success, with the `discount_code`
- [ ] (demo) the phone you use has **joined the Twilio WhatsApp sandbox**

## Quick test (no website needed)
```bash
KEY=...   # from Cart Recovery → Connect your store
BASE=https://foresight-kp1g.onrender.com
curl -X POST $BASE/api/store/event -H "Content-Type: application/json" -H "X-Foresight-Key: $KEY" \
  -d '{"type":"cart_abandoned","cart_id":"c1","customer":{"name":"Asha","phone":"+9162..."},
       "items":[{"name":"Kurta","qty":1,"price":1299}],"value":1299}'
# watch it appear in the Cart Recovery dashboard, then send a purchase with the issued code
```
